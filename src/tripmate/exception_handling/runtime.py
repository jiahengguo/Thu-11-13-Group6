"""EXC-01/02 deterministic prototype; structured simulated sources only."""
from copy import deepcopy
from datetime import datetime, timezone, timedelta
from decimal import Decimal, InvalidOperation
from uuid import uuid4
import sqlite3
from tripmate.contracts import validate, ContractError
from .contracts import validate_context


def now():
    return datetime.now(timezone.utc).isoformat()


def instant(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('Timezone required')
    return parsed


def money(value):
    from .contracts import MONEY
    import re
    if not isinstance(value, str) or not re.fullmatch(MONEY['pattern'], value):
        raise ValueError('Non-negative AUD cents required')
    return Decimal(value)


def envelope(case, sources):
    return dict(schemaVersion='1.0.0', caseId=case['caseId'], correlationId=case['correlationId'],
                sourceReferences=deepcopy(sources), validationResults=[], errors=[], requiresApproval=False)


class Referral(Exception):
    def __init__(self, code, reason):
        self.code, self.reason = code, reason


class ExceptionRuntime:
    def __init__(self, contexts, repository, supplier, planning, reviewer, *, clarification=False, complaint_findings=None):
        self.contexts, self.repository = contexts, repository
        self.supplier, self.planning, self.reviewer = supplier, planning, reviewer
        self.clarification = clarification
        self.complaint_findings = complaint_findings

    def handle_case(self, supplied_case):
        validate('Case', supplied_case)
        case = deepcopy(supplied_case)
        result = envelope(case, case['sourceReferences'])
        result.update(runId=str(uuid4()), agent='exception', status='HUMAN_ASSISTANCE',
                      executionMode='FIXTURE', findings=[], proposedResponse=None, subjects=[],
                      review=None, approvalIds=[], nextAction='Operations must coordinate human handling; keep the case open.')
        result['requiresApproval'] = case['requiresApproval']
        snapshot = dict(recordedAt=now(), assessedAt=None, result=result, inputCase=case,
                        context=None, proposal=None, approvals=[], trace=[], handoffTo='operations',
                        caseRemainsOpen=True, modelExecution='NONE',
                        dependencies={'operations': 'CONFIRMED_FIXTURE_HANDOFF', 'supplier': 'SIMULATED',
                                      'planning': 'SIMULATED', 'reviewer': 'SIMULATED_RULES'},
                        note='Local simulation. No traveller contact, booking change or financial transaction.')
        snapshot['dependencies'].update(supplier=type(self.supplier).__name__, planning=type(self.planning).__name__)
        case_subject = dict(subjectType='Case', subjectId=case['caseId'], materialVersion=1)

        def event(kind, summary, outcome='SUCCESS', subject=None, approval=None):
            e = envelope(case, result['sourceReferences'])
            e.update(requiresApproval=result['requiresApproval'], eventId=str(uuid4()), runId=result['runId'],
                     timestamp=now(), actor='exception', eventType=kind, subject=subject or case_subject,
                     parentEventId=snapshot['trace'][-1]['eventId'] if snapshot['trace'] else None,
                     executionMode='FIXTURE', summary=summary, result=outcome, approvalId=approval)
            if kind in {'VALIDATION', 'REVIEW', 'FAILURE', 'HANDOFF'}:
                e['validationResults'] = deepcopy(result['validationResults'])
                e['errors'] = deepcopy(result['errors'])
            snapshot['trace'].append(e)

        def check(rule, ok, reason, code='HUMAN_ASSISTANCE_REQUIRED', ids=None):
            row = dict(ruleId=rule, ruleVersion='exception-fixture-1', outcome='PASS' if ok else 'FAIL',
                       reason=reason, checkedAt=now(), sourceIds=ids or [])
            result['validationResults'].append(row)
            event('VALIDATION', reason, 'SUCCESS' if ok else 'FAILURE')
            if not ok:
                raise Referral(code, reason)

        event('INTAKE', 'Received specialist handoff from Operations; no external response sent.')
        try:
            check('EXC_INTAKE', case['caseKind'] == 'CUSTOMER' and case['caseType'] in {'DISRUPTION', 'COMPLAINT'}
                  and case['coordinator'] == 'operations' and case['primaryHandler'] == 'exception'
                  and case['status'] in {'CONFIRMED', 'ASSIGNED', 'IN_PROGRESS'},
                  'Only an open, confirmed CustomerCase assigned to Exception is supported.', 'UNCONFIRMED_REQUEST')
            check('EXC_CONFIRMATION_GAPS', not case['unresolvedQuestions'],
                  'Confirmed request must have no unresolved intake questions.', 'MISSING_REQUIRED_FIELDS')
            check('EXC_MANUAL_REQUEST', case['humanRequestCount'] < 2,
                  'Repeated explicit human requests require Operations human assistance.')
            ctx = self.contexts.load(case['caseId'])
            validate_context(ctx)
            if 'planningContext' in ctx:
                request = ctx['planningContext']['request']
                check('EXC_PLANNING_CONTEXT', request['caseId'] == case['caseId']
                      and request['correlationId'] == case['correlationId']
                      and request['travellerId'] == case['requesterId'],
                      'Planning context must bind to this confirmed Operations case.', 'ACCESS_DENIED')
            if ctx['issue']['requestedActions']:
                result['requiresApproval'] = True
            snapshot['context'] = deepcopy(ctx)
            snapshot['assessedAt'] = ctx['assessedAt']
            check('EXC_CONTEXT_OWNER', ctx['caseId'] == case['caseId'] and
                  ctx['travellerId'] == case['requesterId'] == ctx['itinerary']['travellerId'] and
                  ctx['issue']['kind'] == case['caseType'], 'Context must match case type and traveller.', 'ACCESS_DENIED')
            check('EXC_SIMULATION', all(s['simulated'] for s in case['sourceReferences']) and
                  all(e['source']['simulated'] for e in ctx['evidence']),
                  'This runtime accepts explicitly simulated sources only.', 'INVALID_CONTRACT')
            # Retain original source provenance; duplicate IDs may never redefine a source.
            sources = {s['sourceId']: s for s in result['sourceReferences']}
            check('EXC_INTAKE_SOURCE_IDS', len(sources) == len(result['sourceReferences']),
                  'Intake source identifiers must be unique.', 'INVALID_CONTRACT')
            evidence_ids = [e['source']['sourceId'] for e in ctx['evidence']]
            check('EXC_EVIDENCE_IDS', len(evidence_ids) == len(set(evidence_ids)),
                  'Evidence identifiers must be unique.', 'INVALID_CONTRACT')
            for e in ctx['evidence']:
                s = e['source']
                check('EXC_SOURCE_IDENTITY', s['sourceId'] not in sources or sources[s['sourceId']] == s,
                      'A source ID must retain its original provenance.', 'INVALID_CONTRACT')
                sources[s['sourceId']] = s
            result['sourceReferences'] = list(sources.values())
            at = instant(ctx['assessedAt'])
            check('EXC_INTAKE_TIME', instant(case['createdAt']) <= instant(case['confirmedAt']) <= at,
                  'Confirmation must precede the scenario assessment time.', 'UNCONFIRMED_REQUEST')
            check('EXC_SOURCE_FRESHNESS', all(s['freshness'] == 'FRESH' and instant(s['capturedAt']) <= at
                  for s in sources.values()) and all(instant(e['validUntil']) > at for e in ctx['evidence']),
                  'Sources must be fresh at the explicitly recorded scenario time.', 'STALE_EVIDENCE', list(sources))
            facts = {}
            for evidence in ctx['evidence']:
                for assertion in evidence['assertions']:
                    facts.setdefault(assertion['key'], []).append((assertion['value'], evidence['source']['sourceId']))
            conflicts = [key for key, values in facts.items() if len({v for v, _ in values}) > 1]
            check('EXC_EVIDENCE_CONSISTENCY', not conflicts,
                  'Conflicting evidence: ' + ', '.join(conflicts) if conflicts else 'No conflicting structured facts.',
                  ids=[s for k in conflicts for _, s in facts[k]])
            check('EXC_CONFIDENCE', ctx['issue']['confidence'] == 'SUFFICIENT',
                  'Source assessment must be sufficient; LOW or UNKNOWN requires human handling.', 'LOW_CONFIDENCE')
            check('EXC_LEGAL_SAFETY', not (ctx['issue']['legalConcern'] or ctx['issue']['safetyConcern']),
                  'Legal or safety concerns require human handling.')
            if ctx['issue']['requestedActions']:
                result['requiresApproval'] = True
            items = ctx['itinerary']['items']
            check('EXC_ITEM_IDENTIFIERS', bool(items) and len({i['itemId'] for i in items}) == len(items),
                  'Itinerary item IDs must be unique.', 'INVALID_CONTRACT')
            affected = [i for i in items if i['itemId'] == ctx['issue']['itemId']]
            check('EXC_AFFECTED_ITEM', len(affected) == 1, 'The reported service must resolve to an itinerary item.', 'MISSING_REQUIRED_FIELDS')
            for item in items:
                check('EXC_ITEM_EVIDENCE', set(item['sourceIds']).issubset(sources) and
                      instant(item['startAt']) < instant(item['endAt']),
                      'Original item evidence and schedule checked: ' + item['itemId'], 'INVALID_CONTRACT', item['sourceIds'])
            result['findings'].append('Affected service: ' + affected[0]['itemId'] + '. ' + ctx['issue']['summary'])
            if case['caseType'] == 'DISRUPTION':
                check('EXC_ACTIVE_TRIP', ctx['itinerary']['planStatus'] == 'ACTIVE',
                      'Recovery requires an active baseline itinerary.', 'INVALID_CONTRACT')
                check('EXC_CANCELLATION', facts.get(affected[0]['itemId'] + ':status', [('', '')])[0][0] == 'CANCELLED',
                      'Cancellation must be supported by a referenced structured fact.', 'MISSING_REQUIRED_FIELDS')
                proposal = (self._recover_project(ctx, sources, result['sourceReferences'], check, event)
                            if 'planningContext' in ctx else self._recover(ctx, sources, check, event))
            else:
                if ctx.get('complaintCategory', 'DELAY') != 'DELAY':
                    if self.complaint_findings is None:
                        raise Referral('TOOL_UNAVAILABLE', 'Relevant Planning/Supplier complaint findings are not configured.')
                    findings = self.complaint_findings.investigate(deepcopy(ctx))
                    self._merge_sources(findings['sources'], sources, result['sourceReferences'], ctx, check)
                    result['findings'].extend(findings['findings'])
                    snapshot['specialistFindings'] = deepcopy(findings)
                    event('TOOL_RESULT', 'Retrieved recorded Planning/Supplier facts; no service fault or liability is inferred.')
                    raise Referral('HUMAN_ASSISTANCE_REQUIRED',
                                   'Specialist facts collected. No agreed resolution policy for this complaint category; Operations must refer for human handling.')
                proposal = self._complaint(ctx, sources, facts, check, event)
            previous = self.repository.latest_proposal(case['caseId'])
            subject_type = 'RecoveryProposal' if case['caseType'] == 'DISRUPTION' else 'ResolutionRecommendation'
            previous_ref = previous['proposal']['subject'] if previous else None
            if previous_ref and previous_ref['subjectType'] != subject_type:
                previous_ref = None
            subject = dict(subjectType=subject_type,
                           subjectId=previous_ref['subjectId'] if previous_ref else str(uuid4()),
                           materialVersion=previous_ref['materialVersion'] + 1 if previous_ref else 1)
            proposal['previousSubject'] = deepcopy(previous_ref)
            proposal['previousReviewId'] = (previous['result']['review']['reviewId']
                                            if previous and previous['result']['review'] else None)
            proposal.update(subject=subject, baselineVersionId=ctx['itinerary']['versionId'],
                            sourceIds=list(sources), checks=deepcopy(result['validationResults']),
                            requiresApproval=result['requiresApproval'], simulated=True)
            proposal['assessedAt'] = ctx['assessedAt']
            proposal['evidenceAssertions'] = [dict(sourceId=e['source']['sourceId'], assertions=deepcopy(e['assertions']))
                                               for e in ctx['evidence']]
            snapshot['proposal'] = proposal
            result['subjects'] = [subject]
            event('VERSION_CREATED', 'Created a proposal; original itinerary remains unchanged.', subject=subject)
            review = self.reviewer.review(deepcopy(proposal), deepcopy(result['sourceReferences']), deepcopy(ctx['policies']))
            result['review'] = review
            snapshot['dependencies']['reviewer'] = review['policyVersion'] if review else 'UNAVAILABLE'
            # Validate review shape through the existing result contract before trusting its fields.
            validate('AgentResult', result)
            check('EXC_REVIEW_BINDING', review is not None and review['subject'] == subject and
                  set(review['sourceIds']).issubset(sources), 'Review must reference this exact proposal version and evidence.', 'REVIEW_FAILED')
            event('REVIEW', 'Simulated Reviewer: ' + review['outcome'],
                  'SUCCESS' if review['outcome'] == 'PASS' else 'FAILURE', subject)
            check('EXC_REVIEW', review['outcome'] == 'PASS',
                  'Simulated review passed.' if review['outcome'] == 'PASS' else 'Review requires revision: ' + '; '.join(review['reasons']),
                  'REVIEW_FAILED')
            result['findings'].extend(proposal['findings'])
            result['proposedResponse'] = proposal['recommendation']
            result['status'] = 'SUCCESS'
            result['nextAction'] = 'Operations must review the internal handoff before communicating with the traveller. Case remains open.'
            if result['requiresApproval']:
                approval = envelope(case, result['sourceReferences'])
                approval.update(requiresApproval=True, approvalId=str(uuid4()), subject=subject,
                                scope='Human review of proposed restricted action only: ' +
                                      ', '.join(ctx['issue']['requestedActions'] or ['INHERITED_APPROVAL_REQUIREMENT']),
                                status='PENDING', decision=None, requestedAt=now(), decidedAt=None,
                                operatorId=None, reason=None, reviewId=review['reviewId'])
                snapshot['approvals'].append(approval)
                result['approvalIds'] = [approval['approvalId']]
                result['status'] = 'APPROVAL_PENDING'
                result['nextAction'] = 'Operations must obtain a recorded human decision for this proposal version. No commitment or transaction is authorised.'
                event('APPROVAL_REQUESTED', approval['scope'], 'PENDING', subject, approval['approvalId'])
        except Referral as exc:
            result.update(status='HUMAN_ASSISTANCE', proposedResponse=None)
            if self.clarification and exc.code in {'MISSING_REQUIRED_FIELDS', 'STALE_EVIDENCE', 'REVIEW_FAILED'}:
                result['status'] = 'REVISION_REQUIRED'
                result['nextAction'] = 'Operations must obtain and confirm clarification/correction, then resume this same case. ' + exc.reason
            result['errors'].append(dict(code=exc.code, message=exc.reason, step='exception_investigation', retryable=False, sourceIds=[]))
            result['findings'].append(exc.reason)
            event('FAILURE', exc.reason, 'FAILURE')
        except (ContractError, ValueError, TypeError, KeyError, InvalidOperation):
            result.update(status='HUMAN_ASSISTANCE', proposedResponse=None, review=None)
            result['errors'].append(dict(code='INVALID_CONTRACT', message='Structured context or dependency output is invalid or missing.',
                                         step='exception_investigation', retryable=False, sourceIds=[]))
            event('FAILURE', 'Invalid input/dependency data requires human handling.', 'FAILURE')
        except Exception:
            result.update(status='HUMAN_ASSISTANCE', proposedResponse=None, review=None)
            result['errors'].append(dict(code='TOOL_UNAVAILABLE', message='A required dependency failed; investigation is incomplete.',
                                         step='dependency', retryable=True, sourceIds=[]))
            event('FAILURE', 'Dependency unavailable; Operations must coordinate assistance.', 'FAILURE')
        if result['status'] == 'HUMAN_ASSISTANCE':
            snapshot['referral'] = dict(reason=[e['message'] for e in result['errors']],
                                       unresolvedQuestions=case['unresolvedQuestions'], evidenceIds=[s['sourceId'] for s in result['sourceReferences']],
                                       to='operations', humanHandlingRequired=True)
        elif result['status'] == 'REVISION_REQUIRED':
            snapshot['clarification'] = dict(to='operations', questions=[e['message'] for e in result['errors']],
                                             requiresConfirmation=True, caseRemainsOpen=True)
        event('HANDOFF', 'Internal result prepared for Operations; traveller delivery has not occurred.', 'PENDING')
        validate('AgentResult', result)
        try:
            self.repository.save(snapshot)
        except (sqlite3.Error, OSError):
            # A returned proposal must never claim success unless the complete snapshot was saved.
            result.update(status='FAILURE', proposedResponse=None, subjects=[], review=None, approvalIds=[],
                          nextAction='Operations must keep the case open and retry persistence or obtain human assistance.')
            result['errors'] = [dict(code='PERSISTENCE_FAILED', message='Could not save investigation and handoff; no completed result is claimed.',
                                    step='save', retryable=True, sourceIds=[])]
            validate('AgentResult', result)
        return result

    @staticmethod
    def _merge_sources(new_sources, sources, sink, ctx, check):
        for source in new_sources:
            check('EXC_PROJECT_SOURCE', source['simulated'] and source['freshness'] == 'FRESH'
                  and instant(source['capturedAt']) <= instant(ctx['assessedAt'])
                  and (source['sourceId'] not in sources or sources[source['sourceId']] == source),
                  'Project dependency sources must be current, simulated and consistent.', 'STALE_EVIDENCE')
            sources[source['sourceId']] = deepcopy(source)
            sink[:] = list(sources.values())

    def _recover_project(self, ctx, sources, sink, check, event):
        planning = ctx['planningContext']
        baseline = planning['baseline']
        check('EXC_PLANNING_BASELINE', baseline['version']['versionId'] == ctx['itinerary']['versionId']
              and baseline['version']['travellerId'] == ctx['travellerId'] and not ctx['constraints'],
              'Use the owned baseline and the complete confirmed Planning constraint set; extra unbound constraints require clarification.',
              'UNSUPPORTED_CONSTRAINT')
        affected = [i for i in baseline['version']['items'] if i['itemId'] == ctx['issue']['itemId']]
        check('EXC_PLANNING_AFFECTED', len(affected) == 1, 'Cancelled item must resolve to the Planning baseline.', 'MISSING_REQUIRED_FIELDS')
        affected_offer = affected[0]['offerId']
        affected_quote = next(q for q in baseline['quotes'] if q['offer']['offerId'] == affected_offer)
        role = affected_quote['product']['role']
        unchanged = {i['offerId'] for i in baseline['version']['items']} - {affected_offer}
        quotes = self.supplier.alternatives(deepcopy(ctx))
        quotes = [q for q in quotes if q['offer']['offerId'] != affected_offer
                  and (q['product']['role'] == role or q['offer']['offerId'] in unchanged)]
        for quote in quotes:
            self._merge_sources(quote['offer']['sourceReferences'] + quote['price']['sourceReferences'], sources, sink, ctx, check)
        event('TOOL_RESULT', 'Queried the project Supplier lookup; excluded the cancelled offer and retained unaffected arrangements.')
        records, excluded = self.planning.recover(deepcopy(ctx), deepcopy(quotes))
        options, rejected = [], [{'offerId': ','.join(e['offerIds']),
                                  'reasons': [c['reason'] for c in e['checks'] if c['outcome'] != 'PASS'],
                                  'sourceIds': []} for e in excluded]
        for record in records:
            version = record['version']
            validate('ItineraryVersion', version)
            if (not unchanged <= {i['offerId'] for i in version['items']}
                    or any(c['outcome'] != 'PASS' for c in version['validationResults'])):
                continue
            total = money(ctx['itinerary']['sunkCost']) + money(version['totalPrice']['amount'])
            if total > money(planning['request']['budgetCeiling']['amount']):
                rejected.append(dict(offerId=version['versionId'], reasons=['Sunk plus candidate cost exceeds the confirmed budget.'], sourceIds=[]))
                continue
            products = {q['offer']['offerId']: q for q in record['quotes']}
            items = [dict(itemId=i['itemId'], kind={'TRANSPORT':'TRANSPORT','ACCOMMODATION':'HOTEL','ACTIVITY':'ACTIVITY'}[i['productType']],
                          origin=i['origin'], destination=i['destination'], startAt=i['startAt'], endAt=i['endAt'],
                          remainingCost=i['quotedPrice']['amount'], sourceIds=i['sourceIds']) for i in version['items']]
            replacement = next(i for i in version['items'] if products[i['offerId']]['product']['role'] == role)
            options.append(dict(offerId=version['versionId'], items=items, totalCost=f'{total:.2f}', currency='AUD',
                                terms='; '.join(q['offer']['cancellationTerms'] for q in record['quotes']),
                                sourceIds=[s['sourceId'] for s in version['sourceReferences']],
                                arrivalChangeMinutes=int((instant(replacement['endAt'])-instant(affected[0]['endAt'])).total_seconds()/60),
                                planningRecord=record))
        check('EXC_PROJECT_FEASIBLE', bool(options), 'The project Planning engine must return a complete feasible recovery preserving confirmed requirements.',
              'NO_FEASIBLE_ITINERARY')
        event('TOOL_RESULT', 'Project Planning generated and validated candidates using the existing typed constraints and preference ranking.')
        return dict(kind='RECOVERY', options=options, rejectedOptions=rejected, sunkCost=ctx['itinerary']['sunkCost'],
                    affectedItemIds=[ctx['issue']['itemId']], findings=['Existing Planning constraints and preference ranking applied.',
                    'Unaffected arrangements and the original baseline are preserved.'],
                    costBasis='Supplied sunk non-refundable cost plus quoted candidate costs; no assumed refund or credit.',
                    recommendation='Operations: present the validated project recovery options and their cost/time changes. No booking has changed.')

    def _recover(self, ctx, sources, check, event):
        items, affected_id = ctx['itinerary']['items'], ctx['issue']['itemId']
        target = next(i for i in items if i['itemId'] == affected_id)
        check('EXC_RECOVERY_SCOPE', target['kind'] == 'FLIGHT' and sum(i['kind'] == 'FLIGHT' for i in items) == 1,
              'Prototype supports replacement of one flight with later hotel/activity arrangements.', 'UNSUPPORTED_CONSTRAINT')
        constraints = {x['name']: x['value'] for x in ctx['constraints']}
        check('EXC_CONSTRAINT_SCOPE', len(constraints) == len(ctx['constraints']) and
              set(constraints) == {'budgetTotal', 'earliestDeparture', 'latestArrival', 'minTransferMinutes'},
              'All confirmed constraints must be supported; this prototype checks budget and departure/arrival limits.', 'UNSUPPORTED_CONSTRAINT')
        budget = money(constraints['budgetTotal'])
        import re
        if not re.fullmatch(r'[0-9]{1,4}', constraints['minTransferMinutes']):
            raise ValueError('Explicit nonnegative transfer minutes required')
        buffer = timedelta(minutes=int(constraints['minTransferMinutes']))
        earliest, latest = instant(constraints['earliestDeparture']), instant(constraints['latestArrival'])
        check('EXC_CONSTRAINT_WINDOW', earliest < latest, 'Confirmed time window must be coherent.', 'INVALID_CONTRACT')
        offers = self.supplier.alternatives(deepcopy(ctx))
        event('TOOL_RESULT', 'Simulated Supplier returned alternatives with price, availability and terms.')
        eligible, rejected = [], []
        from .contracts import OFFER
        from jsonschema import Draft202012Validator, FormatChecker
        for offer in offers:
            Draft202012Validator(OFFER, format_checker=FormatChecker()).validate(offer)
            reasons = []
            if offer['status'] != 'APPROVED' or not offer['available']:
                reasons.append('Offer is not approved and available.')
            if instant(offer['validUntil']) <= instant(ctx['assessedAt']):
                reasons.append('Offer has expired at the scenario time.')
            replacement = offer['replacement']
            if not set(offer['sourceIds'] + replacement['sourceIds']).issubset(sources):
                reasons.append('Offer evidence is unresolved.')
            if (replacement['kind'] != 'FLIGHT' or replacement['origin'] != target['origin'] or
                    replacement['destination'] != target['destination']):
                reasons.append('Alternative does not cover the affected route.')
            revised = self.planning.revise(deepcopy(ctx), deepcopy(offer))
            expected = [replacement if i['itemId'] == affected_id else i for i in items]
            if revised != expected or len({i['itemId'] for i in revised}) != len(revised):
                reasons.append('Planning changed unaffected items or returned an incomplete itinerary.')
            departure, arrival = instant(replacement['startAt']), instant(replacement['endAt'])
            if not max(earliest, instant(ctx['assessedAt'])) <= departure < arrival <= latest:
                reasons.append('Departure/arrival violates the confirmed time window.')
            if any(instant(i['startAt']) < arrival + buffer for i in items if i['itemId'] != affected_id):
                reasons.append('Arrival plus the supplied transfer allowance misses a downstream hotel or activity start.')
            total = money(ctx['itinerary']['sunkCost']) + sum((money(i['remainingCost']) for i in revised), Decimal('0.00'))
            if total > budget:
                reasons.append('Total cost exceeds the confirmed budget.')
            if reasons:
                rejected.append(dict(offerId=offer['offerId'], reasons=reasons, sourceIds=offer['sourceIds']))
            else:
                eligible.append(dict(offerId=offer['offerId'], items=revised, totalCost=f'{total:.2f}',
                                     currency='AUD', terms=offer['terms'], sourceIds=offer['sourceIds'],
                                     arrivalChangeMinutes=int((arrival - instant(target['endAt'])).total_seconds() / 60)))
        event('TOOL_RESULT', 'Simulated Planning candidates checked; rejected options retained in the investigation.')
        # Retain exclusions even when no valid plan can be produced.
        ctx['candidateAssessment'] = {'eligible': eligible, 'rejected': rejected}
        check('EXC_FEASIBLE_OPTION', bool(eligible),
              'At least one alternative meets every supported constraint.' if eligible else
              'No feasible alternative. ' + '; '.join(r['offerId'] + ': ' + ', '.join(r['reasons']) for r in rejected),
              'NO_FEASIBLE_ITINERARY')
        return dict(kind='RECOVERY', options=eligible, rejectedOptions=rejected,
                    sunkCost=ctx['itinerary']['sunkCost'],
                    affectedItemIds=[affected_id] + [i['itemId'] for i in items if i['itemId'] != affected_id],
                    costBasis='Sunk non-refundable cost + all revised remaining costs. No assumed refund or credit.',
                    findings=['Transport, hotel and activity timing assessed; all confirmed constraints preserved.',
                              'All eligible alternatives are returned without introducing a new ranking rule.'],
                    recommendation='Operations: present the checked recovery options and cost/time changes for traveller consideration. No booking has changed.')

    def _complaint(self, ctx, sources, facts, check, event):
        item_id = ctx['issue']['itemId']
        keys = [item_id + ':scheduledArrival', item_id + ':actualArrival']
        check('EXC_SERVICE_RECORDS', all(k in facts for k in keys),
              'Both scheduled and actual arrival evidence are required for this delay investigation.', 'MISSING_REQUIRED_FIELDS')
        scheduled, actual = (instant(facts[k][0][0]) for k in keys)
        target = next(i for i in ctx['itinerary']['items'] if i['itemId'] == item_id)
        check('EXC_SCHEDULE_MATCH', scheduled == instant(target['endAt']),
              'Service schedule must match the affected baseline item; discrepancies require clarification.')
        check('EXC_OBSERVED_SERVICE', actual <= instant(ctx['assessedAt']) and actual > scheduled,
              'Recorded service must establish a past delay; no assumed service failure.', 'HUMAN_ASSISTANCE_REQUIRED')
        policies = ctx['policies']
        check('EXC_POLICY', len(policies) == 1 and set(policies[0]['sourceIds']).issubset(sources),
              'Exactly one explicitly supplied simulated delay policy with evidence is required.', 'MISSING_REQUIRED_FIELDS')
        policy = policies[0]
        evidence_by_id = {e['source']['sourceId']: e for e in ctx['evidence']}
        policy_facts = {'policy:' + policy['policyId'] + ':version': policy['version'],
                        'policy:' + policy['policyId'] + ':action': policy['action']}
        check('EXC_POLICY_EVIDENCE', all(
              sid in evidence_by_id and all(any(a['key'] == key and a['value'] == value
              for a in evidence_by_id[sid]['assertions']) for key, value in policy_facts.items())
              for sid in policy['sourceIds']),
              'The policy version and proposed action must be supported by every referenced policy source.')
        minutes = int((actual - scheduled).total_seconds() / 60)
        event('TOOL_RESULT', 'Simulated service records and policy evaluated with deterministic elapsed-time calculation.')
        recommendation = 'Operations: explain the recorded delay and offer an apology under the supplied simulated policy. No refund or compensation entitlement is determined.'
        if policy['action'] == 'HUMAN_REVIEW_REFUND':
            check('EXC_REFUND_REQUEST', 'REFUND' in ctx['issue']['requestedActions'],
                  'Refund-review policy requires an explicit restricted-action request.')
            recommendation = 'Operations: refer the refund request for a human decision. Eligibility and amount are undetermined; no refund is authorised.'
        return dict(kind='COMPLAINT', delayMinutes=minutes, policyIds=[policy['policyId']],
                    affectedItemIds=[item_id],
                    findings=[f'Referenced service records establish a {minutes}-minute arrival delay.',
                              'Policy: ' + policy['policyId'] + ' version ' + policy['version']],
                    recommendation=recommendation)
