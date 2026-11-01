"""UC-08 simulated campaigns: sourced drafts, atomic decisions and UC-06 quotes.

No channel SDK, publication, spending or autonomous approval is implemented.
The LLM chooses constrained copy; prices, terms, budgets and discounts are facts.
"""
import hashlib
import json
import re
from copy import deepcopy
from decimal import Decimal

from jsonschema import Draft202012Validator, FormatChecker
from tripmate.operations.common import OperationsError, envelope, identifier, instant, source, safe_text
from tripmate.services.review import DeterministicReviewService
from .common import validate_offer, verify_price, SupplierError


POLICY = 'simulated-campaign-1'
CHANNELS = {'SIMULATED_EMAIL': {'unitCost': '2.00', 'fixedCost': '10.00'},
            'SIMULATED_SOCIAL': {'unitCost': '1.00', 'fixedCost': '5.00'}}
INTROS = ['Explore these approved simulated travel offers.',
          'Compare sourced travel offers for your next domestic trip.']
RESTRICTIONS = ['No personal targeting', 'No guaranteed outcomes', 'No real booking or payment claims']
MONEY = {'type': 'string', 'pattern': r'^(0|[1-9][0-9]*)\.[0-9]{2}$', 'maxLength': 12}
TEXT = {'type': 'string', 'minLength': 1, 'maxLength': 300}
INSTANT = {'type': 'string', 'format': 'date-time'}
BRIEF = {'type': 'object', 'additionalProperties': False, 'properties': {
    'objective': TEXT, 'audience': TEXT, 'audienceTiers': {'type': 'array', 'minItems': 1,
        'uniqueItems': True, 'items': {'enum': ['FREE', 'PAID']}},
    'channel': {'enum': list(CHANNELS)}, 'startAt': INSTANT, 'endAt': INSTANT,
    'budget': MONEY, 'units': {'type': 'integer', 'minimum': 1, 'maximum': 100000},
    'restrictions': {'type': 'array', 'minItems': 1, 'maxItems': 3, 'uniqueItems': True, 'items': {'enum': RESTRICTIONS}},
    'offerIds': {'type': 'array', 'minItems': 1, 'maxItems': 8, 'uniqueItems': True,
                 'items': {'type': 'string', 'minLength': 1, 'maxLength': 100}},
    'memberOffer': {'oneOf': [{'type': 'null'}, {'type': 'object', 'additionalProperties': False,
        'properties': {'eligibleTiers': {'type': 'array', 'minItems': 1, 'uniqueItems': True,
                                       'items': {'enum': ['FREE', 'PAID']}},
                       'discount': MONEY, 'validFrom': INSTANT, 'validUntil': INSTANT},
        'required': ['eligibleTiers', 'discount', 'validFrom', 'validUntil']}]}
}, 'required': ['objective', 'audience', 'audienceTiers', 'channel', 'startAt', 'endAt',
                'budget', 'units', 'restrictions', 'offerIds', 'memberOffer']}
COPY_SCHEMA = {'type': 'object', 'additionalProperties': False,
    'properties': {'intro': {'enum': INTROS}}, 'required': ['intro']}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def cents(value):
    return {'amount': str(value.quantize(Decimal('.01'))), 'currency': 'AUD'}


def error(message, code='INVALID_CONTRACT'):
    raise OperationsError(code, message)


class CampaignService:
    def __init__(self, operations, supplier):
        self.ops, self.supplier = operations, supplier
        self.repo = operations.repository
        operations.campaigns = self
        operations.entitlement.member_offer_check = self.member_offer_check
        self.reviewer = DeterministicReviewService(lambda: operations.clock(),
            {'CampaignProposal': self._review_domain})

    def operator(self, actor):
        profile = self.ops.profile(actor)
        if not profile or not profile.get('verified') or profile.get('role') != 'OPERATOR':
            error('Only a verified Operator can manage campaigns.', 'ACCESS_DENIED')

    def _record(self, campaign_id):
        value = self.repo.read('campaign', campaign_id)
        if not value or value.get('schemaVersion') != 'campaign-1':
            error('Campaign not found.', 'ACCESS_DENIED')
        return value

    def _current(self, rows, body):
        record = rows.get('campaign', body['campaignId'])
        if not record or type(body['revision']) is not int or record['revision'] != body['revision']:
            error('Reload the current campaign before making another change.', 'UNCONFIRMED_REQUEST')
        return deepcopy(record)

    def _event(self, rows, record, kind, actor, summary):
        at = self.ops.clock()
        event = envelope(None, record['campaignId'],
                         record.get('proposal', {}).get('sourceReferences') or
                         [source('campaign-brief:' + record['campaignId'], at)])
        event.update(eventId=identifier(), runId=None, timestamp=at, actor='supplier', eventType=kind,
            subject={'subjectType': 'CampaignProposal', 'subjectId': record['campaignId'],
                     'materialVersion': record['materialVersion']}, parentEventId=record.get('lastEventId'),
            executionMode='FIXTURE', summary=summary, result='PENDING' if not record['approved'] else 'SUCCESS',
            approvalId=record.get('approvalId'))
        event['requiresApproval'] = True
        rows.trace(event)
        history = dict(eventId=event['eventId'], actorId=actor, timestamp=at, eventType=kind,
                       materialVersion=record['materialVersion'], summary=summary,
                       status=record['status'], decision=deepcopy(record.get('decision')))
        rows.put('campaign_history', event['eventId'], dict(history, campaignId=record['campaignId']))
        record['lastEventId'] = event['eventId']
        record['revision'] += 1
        rows.put('campaign', record['campaignId'], record)

    def catalog(self, actor):
        self.operator(actor)
        offers = self.supplier.find_selectable({}, self.ops.clock())
        return {'channels': deepcopy(CHANNELS), 'policyVersion': POLICY,
            'draftingReady': self.ops.llm is not None,
            'offers': [dict(offerId=b['offer']['offerId'], materialVersion=b['offer']['materialVersion'],
                productId=b['offer']['productId'], sellingPrice=b['price']['sellingPrice'],
                validFrom=b['offer']['validFrom'], validUntil=b['offer']['validUntil'],
                cancellationTerms=b['offer']['cancellationTerms']) for b in offers]}

    def listing(self, actor):
        self.operator(actor)
        return {'campaigns': [dict(campaignId=r['campaignId'], status=r['status'],
            revision=r['revision'], materialVersion=r['materialVersion'], objective=r['brief'].get('objective', 'Incomplete brief'))
            for r in self.repo.list('campaign') if r.get('schemaVersion') == 'campaign-1']}

    def _brief(self, value):
        if not Draft202012Validator(BRIEF, format_checker=FormatChecker()).is_valid(value):
            error('Complete the objective, audience, channel, dates, budget, units, restrictions and selected offers.')
        for text in [value['objective'], value['audience'], *value['restrictions']]:
            if not text.strip() or re.search(r'@|\b(?:password|bearer|api.key)\b', text, re.I):
                error('Use non-personal campaign descriptions and restrictions; do not include contacts or secrets.')
        if (not instant(value['startAt']) < instant(value['endAt'])
                or instant(value['endAt']) <= instant(self.ops.clock())):
            error('Campaign dates must increase and the campaign must not have ended.')
        rule = value['memberOffer']
        if rule and (Decimal(rule['discount']) <= 0 or
                not instant(value['startAt']) <= instant(rule['validFrom']) < instant(rule['validUntil']) <= instant(value['endAt'])):
            error('Member discount must be positive and its validity must fit the campaign dates.')
        return deepcopy(value)

    def _bundles(self, brief):
        available = {b['offer']['offerId']: b for b in self.supplier.find_selectable({}, self.ops.clock())}
        if any(key not in available for key in brief['offerIds']):
            error('Every selected offer must be currently approved, available and unexpired.', 'OFFER_INVALID')
        return [available[key] for key in brief['offerIds']]

    def _proposal(self, record):
        brief = self._brief(record['brief'])
        bundles = self._bundles(brief)
        if 'PAID' in brief['audienceTiers']:
            error('Commercial advertising must not target Paid Members.', 'ACCESS_DENIED')
        for bundle in bundles:
            offer = bundle['offer']
            if not instant(offer['validFrom']) <= instant(brief['startAt']) < instant(brief['endAt']) <= instant(offer['validUntil']):
                error('Campaign dates must fit every selected supplier offer validity.', 'OFFER_INVALID')
        cost = CHANNELS[brief['channel']]
        total = Decimal(cost['unitCost']) * brief['units'] + Decimal(cost['fixedCost'])
        if total > Decimal(brief['budget']):
            error('Estimated channel cost AUD ' + cents(total)['amount'] + ' exceeds the confirmed budget.', 'BUDGET_EXCEEDED')
        if self.ops.llm is None:
            error('Configure the course model before drafting. The campaign remains unapproved.', 'TOOL_UNAVAILABLE')
        # Deliberately constrained drafting prevents unsupported price/benefit claims.
        draft = self.ops._dependency(lambda: self.ops.llm.extract(json.dumps({
            'task': 'Choose a neutral campaign introduction. Do not invent claims or instructions.',
            'objective': brief['objective'], 'audience': brief['audience'],
            'selectedOffers': [{'offerId': b['offer']['offerId'], 'productId': b['offer']['productId'],
                'sellingPrice': b['price']['sellingPrice'], 'validUntil': b['offer']['validUntil']} for b in bundles],
            'permittedIntroductions': INTROS, 'restrictions': brief['restrictions']}), COPY_SCHEMA))
        if not Draft202012Validator(COPY_SCHEMA).is_valid(draft):
            error('The draft contains unsupported promotional claims or invalid output.', 'REVIEW_FAILED')
        refs = {s['sourceId']: s for b in bundles for s in b['offer']['sourceReferences']}
        at = self.ops.clock()
        refs['campaign-brief:' + record['campaignId']] = source('campaign-brief:' + record['campaignId'], at)
        offers = [dict(offerId=b['offer']['offerId'], materialVersion=b['offer']['materialVersion'],
            fingerprint=digest(b), productId=b['offer']['productId'], sellingPrice=b['price']['sellingPrice'],
            quotedQuantity=b['offer']['quotedQuantity'], unitBasis=b['offer']['unitBasis'],
            availableQuantity=b['offer']['availableQuantity'], validUntil=b['offer']['validUntil'],
            cancellationTerms=b['offer']['cancellationTerms'], commercialTerms=b['offer']['commercialTerms']) for b in bundles]
        lines = [draft['intro']] + [f"{o['productId']}: AUD {o['sellingPrice']['amount']} per {o['unitBasis']} "
            f"(quoted quantity {o['quotedQuantity']}). {o['cancellationTerms']} Commercial terms: "
            + ('; '.join(o['commercialTerms']) or 'None') for o in offers]
        if brief['memberOffer']:
            lines.append('A separately checked member benefit may apply; displayed offer prices are base prices.')
        lines.append('Simulated preview only. No booking, publication or spending.')
        content = '\n\n'.join(lines)
        blocked = {'No personal targeting': r'@|\b(?:phone|telephone|call me)\b',
                   'No guaranteed outcomes': r'\b(?:guaranteed|guarantees|guarantee|risk.free)\b',
                   'No real booking or payment claims': r'\b(?:booking confirmed|payment completed|already booked|already paid)\b'}
        if any(re.search(blocked[key], content, re.I) for key in brief['restrictions']):
            error('Sourced copy conflicts with a confirmed content/privacy restriction.', 'REVIEW_FAILED')
        return dict(campaignId=record['campaignId'], materialVersion=record['materialVersion'],
            sourceReferences=list(refs.values()), offers=offers, brief=brief, content=content,
            rationale='Selected approved offers support the confirmed objective: ' + brief['objective'],
            draftedAt=at, draftingMode='CONSTRAINED_MODEL', policyVersion=POLICY,
            costItems={'units': brief['units'], **cost, 'total': cents(total)},
            validationResults=[dict(ruleId=key, ruleVersion=POLICY, outcome='PASS', reason='Checked against confirmed inputs.',
                checkedAt=at, sourceIds=list(refs)) for key in ['BUDGET', 'DATES', 'OFFER_EVIDENCE', 'PAID_AD_DENIAL', 'SOURCED_CONTENT']])

    def _review_domain(self, proposal, evidence, policies):
        if POLICY not in policies or proposal.get('policyVersion') != POLICY:
            return ['The configured campaign policy is required.']
        return [] if proposal.get('offers') and proposal.get('content', '').endswith('No booking, publication or spending.') else ['Incomplete sourced preview.']

    def require_live(self, rows, record):
        """Check the exact authority and source snapshots inside the committing transaction."""
        proposal = record.get('proposal') if record else None
        if not proposal or not record.get('approved') or record.get('status') != 'APPROVED':
            error('The campaign has no current human approval.', 'ACCESS_DENIED')
        self._fresh(rows, proposal)
        return record

    def _fresh(self, rows, proposal):
        at = instant(self.ops.clock())
        if at >= instant(proposal['brief']['endAt']) or proposal['policyVersion'] != POLICY:
            error('Campaign expired or policy changed; create and approve a new revision.', 'STALE_EVIDENCE')
        for snapshot in proposal['offers']:
            pointer = rows.get('supplier_current', snapshot['offerId'])
            current = rows.get('supplier_version', self.supplier.repository.key(snapshot['offerId'], snapshot['materialVersion']))
            if (not pointer or pointer.get('invalidated') or pointer['version'] != snapshot['materialVersion']
                    or not current or not current.get('offer') or current['offer']['status'] != 'APPROVED'):
                error('Supplier material changed; revise and reassess the campaign.', 'STALE_EVIDENCE')
            # find_selectable returns only this public bundle, not storage metadata.
            bundle = {key: current[key] for key in ('offer', 'price')}
            if current.get('product'):
                bundle['product'] = current['product']
            if digest(bundle) != snapshot['fingerprint'] or at >= instant(current['offer']['validUntil']):
                error('Supplier evidence or price changed; fresh campaign approval is required.', 'STALE_EVIDENCE')
            case = rows.get('case', current['caseId'])
            if not case or case['case']['status'] == 'WITHDRAWN':
                error('A selected supplier source was withdrawn.', 'STALE_EVIDENCE')
            try:
                validate_offer(current['offer'], self.ops.clock())
                verify_price(current['offer'], current['price'], self.supplier.policy)
            except (SupplierError, ValueError):
                error('Current supplier validation or pricing policy no longer passes.', 'STALE_EVIDENCE')
            if current['offer']['requiresApproval']:
                approval = rows.get('supplier_approval', current['offer']['approvalId'] + '/DECIDED')
                profile = self.ops.profile(approval['operatorId']) if approval else None
                if (not approval or approval.get('decision') != 'APPROVE' or not profile
                        or not profile.get('verified') or profile.get('role') != 'OPERATOR'):
                    error('Restricted supplier approval is no longer authorised.', 'STALE_EVIDENCE')

    def view(self, actor, campaign_id):
        self.operator(actor)
        record = self._record(campaign_id)
        record['usable'] = False
        if record['approved']:
            # Reopening an expired/changed campaign cannot expose a usable approval.
            with self.repo.transaction() as rows:
                current = rows.get('campaign', campaign_id)
                try:
                    if current['revision'] != record['revision'] or not current['approved']:
                        return dict(deepcopy(current), usable=False, history=[h for h in
                            self.repo.list('campaign_history') if h['campaignId'] == campaign_id])
                    self.require_live(rows, current)
                    record['usable'] = True
                except OperationsError as exc:
                    current.update(approved=False, approvalId=None, status='REVISION_REQUIRED', issues=[str(exc)])
                    rule_id = current.get('memberOfferRuleId')
                    if rule_id:
                        rule = rows.get('member_offer', rule_id)
                        if rule:
                            rows.put('member_offer', rule_id, dict(rule, approved=False))
                    self._event(rows, current, 'VALIDATION', actor, 'Campaign authority invalidated: ' + str(exc))
                    record = dict(deepcopy(current), usable=False)
        record['history'] = [h for h in self.repo.list('campaign_history') if h['campaignId'] == campaign_id]
        return record

    def mutate(self, actor, action, body):
        self.operator(actor)
        shapes = {'save': {'requestKey', 'campaignId', 'revision', 'brief', 'confirmed'},
                  'evaluate': {'requestKey', 'campaignId', 'revision'},
                  'decide': {'requestKey', 'campaignId', 'revision', 'decision', 'reason'}}
        if action not in shapes or set(body) != shapes[action]:
            error('Use the current campaign action fields.')
        if (body['campaignId'] is not None and (not isinstance(body['campaignId'], str) or not 1 <= len(body['campaignId']) <= 100)
                or type(body['revision']) is not int or body['revision'] < 0
                or action != 'save' and body['campaignId'] is None):
            error('Supply a valid campaign ID and revision.')
        if action == 'save':
            if body['confirmed'] is not True:
                error('Explicitly confirm the campaign brief before saving.', 'UNCONFIRMED_REQUEST')
            brief = self._brief(body['brief'])
        prepared, failure = None, None
        identity = self.ops._command_identity(actor, 'campaign-' + action, body['requestKey'], body)
        cached, result = self.repo.cached(*identity)
        if cached:
            return result
        if action == 'evaluate':
            record = self._record(body['campaignId'])
            if record['revision'] != body['revision'] or record['status'] != 'DRAFT':
                error('Save a confirmed new revision before evaluating.', 'UNCONFIRMED_REQUEST')
            try:
                prepared = self._proposal(record)
            except Exception as exc:
                failure = {'code': getattr(exc, 'code', 'TOOL_UNAVAILABLE'),
                           'message': str(exc) if isinstance(exc, OperationsError) else 'Drafting failed; check the configured model and retry manually.'}
        if action == 'decide':
            if body['decision'] not in {'APPROVE', 'REQUEST_REVISION', 'REJECT'}:
                error('Choose Approve, Request revision or Reject.')
            if not isinstance(body['reason'], str) or not 1 <= len(body['reason'].strip()) <= 1000:
                error('Record a reason for the exact proposal version.')
            # Re-run the existing authoritative selector, including restricted approvals.
            if body['decision'] == 'APPROVE':
                self._bundles(self._record(body['campaignId'])['brief'])

        def commit(rows):
            if action == 'save':
                old = self._current(rows, body) if body['campaignId'] is not None else None
                if old and old.get('memberOfferRuleId'):
                    rule = rows.get('member_offer', old['memberOfferRuleId'])
                    if rule:
                        rows.put('member_offer', old['memberOfferRuleId'], dict(rule, approved=False))
                record = dict(schemaVersion='campaign-1', campaignId=old['campaignId'] if old else identifier(),
                    materialVersion=old['materialVersion'] + 1 if old else 1, revision=old['revision'] if old else 0,
                    status='DRAFT', approved=False, approvalId=None, decision=None, brief=brief,
                    createdBy=actor, createdAt=self.ops.clock(), issues=[])
                rows.put('campaign_brief', record['campaignId'] + '/' + str(record['materialVersion']), deepcopy(record))
                kind, summary = 'VERSION_CREATED', 'Operator confirmed a new campaign brief; earlier approval cannot authorise this version.'
            else:
                record = self._current(rows, body)
                if action == 'evaluate':
                    if record['status'] != 'DRAFT':
                        error('Save a new brief revision before reevaluation.', 'UNCONFIRMED_REQUEST')
                    if failure:
                        record.update(status='REVISION_REQUIRED', issues=[failure['code'] + ': ' + failure['message']])
                    else:
                        self._fresh(rows, prepared)
                        review = self.reviewer.review(prepared, prepared['sourceReferences'], [POLICY])
                        record.update(proposal=prepared, review=review,
                            status='AWAITING_APPROVAL' if review['outcome'] == 'PASS' else 'REVISION_REQUIRED',
                            issues=deepcopy(review['reasons']))
                        rows.put('campaign_proposal', record['campaignId'] + '/' + str(record['materialVersion']), deepcopy(prepared))
                    kind, summary = 'REVIEW', 'Campaign checks and constrained drafting recorded; human approval is still required.'
                else:
                    if record['status'] != 'AWAITING_APPROVAL' or record['review']['outcome'] != 'PASS':
                        error('Only the current passed proposal may receive a decision.', 'UNCONFIRMED_REQUEST')
                    self._fresh(rows, record['proposal'])
                    decision = dict(decisionId=identifier(), decision=body['decision'], operatorId=actor,
                        materialVersion=record['materialVersion'], reviewId=record['review']['reviewId'],
                        decidedAt=self.ops.clock(), reason=safe_text(body['reason'], 1000))
                    record.update(decision=decision, approved=body['decision'] == 'APPROVE',
                        status={'APPROVE': 'APPROVED', 'REQUEST_REVISION': 'REVISION_REQUIRED', 'REJECT': 'REJECTED'}[body['decision']])
                    record['approvalId'] = decision['decisionId'] if record['approved'] else None
                    rows.put('campaign_decision', decision['decisionId'], dict(decision, campaignId=record['campaignId']))
                    rule = record['brief']['memberOffer']
                    if record['approved'] and rule:
                        rule_id = record['campaignId'] + '/' + str(record['materialVersion'])
                        record['memberOfferRuleId'] = rule_id
                        rows.put('member_offer', rule_id, dict(memberOfferRuleId=rule_id,
                            campaignId=record['campaignId'], materialVersion=record['materialVersion'], approved=True,
                            approvalId=record['approvalId'], eligibleTiers=rule['eligibleTiers'],
                            offerIds=record['brief']['offerIds'], amount={'amount': rule['discount'], 'currency': 'AUD'},
                            validFrom=rule['validFrom'], validUntil=rule['validUntil']))
                    kind, summary = 'APPROVAL_DECIDED', 'Human decision saved for this exact campaign version: ' + body['decision']
            self._event(rows, record, kind, actor, summary)
            return record
        return self.repo.command(*identity, commit)

    def quote(self, actor, body):
        if set(body) != {'requestKey', 'memberOfferRuleId', 'offerId'}:
            error('Supply one approved rule and one applicable offer; discounts do not stack.')
        if any(not isinstance(body[key], str) or not 1 <= len(body[key]) <= 100
               for key in ('memberOfferRuleId', 'offerId')):
            error('Supply valid rule and offer IDs.')
        rule = self.repo.read('member_offer', body['memberOfferRuleId'])
        if not rule:
            error('Approved member offer not found.', 'ACCESS_DENIED')
        record = self._record(rule['campaignId'])
        bundles = self._bundles(record['brief'])
        decision = self.ops.entitlement.evaluate(actor, 'MEMBER_OFFER', {'memberOfferRule': rule})
        if decision['outcome'] != 'ALLOWED' or body['offerId'] not in rule['offerIds']:
            error('Current membership or the selected offer is not eligible.', 'ACCESS_DENIED')
        bundle = next(b for b in bundles if b['offer']['offerId'] == body['offerId'])
        price = self.supplier.pricing.calculate(deepcopy(bundle['offer']), dict(rule,
            eligible=True, entitlementDecisionId=decision['decisionId']))
        def commit(rows):
            current = rows.get('campaign', rule['campaignId'])
            self.require_live(rows, current)
            current_rule = rows.get('member_offer', body['memberOfferRuleId'])
            if current_rule != rule or current.get('memberOfferRuleId') != body['memberOfferRuleId']:
                error('Member offer changed; refresh before requesting a quote.', 'STALE_EVIDENCE')
            rows.put('member_quote', price['priceBreakdownId'], dict(travellerId=actor,
                campaignId=current['campaignId'], materialVersion=current['materialVersion'],
                price=price, entitlement=decision))
            self._event(rows, current, 'VALIDATION', actor, 'Separate UC-06 customer quotation passed UC-07 eligibility and final margin checks.')
            public = {key: deepcopy(price[key]) for key in ('priceBreakdownId', 'offerId', 'offerVersion',
                'basePrice', 'discountAmount', 'sellingPrice', 'quotedQuantity', 'unitBasis',
                'memberOfferRuleId', 'entitlementDecisionId', 'calculatedAt')}
            return {'quotation': public, 'eligibility': {'outcome': decision['outcome'],
                'decisionId': decision['decisionId'], 'reason': decision['reason']}, 'simulated': True}
        return self.ops._command(actor, 'member-quote', body['requestKey'], body, commit)

    def benefits(self, actor):
        profile = self.ops.profile(actor)
        if not profile or not profile.get('verified') or profile.get('role') != 'TRAVELLER':
            error('Member benefits require a verified Traveller.', 'ACCESS_DENIED')
        values = []
        for rule in self.repo.list('member_offer'):
            if self.ops.entitlement.evaluate(actor, 'MEMBER_OFFER', {'memberOfferRule': rule})['outcome'] != 'ALLOWED':
                continue
            campaign = self._record(rule['campaignId'])
            values.append(dict(memberOfferRuleId=rule['memberOfferRuleId'], amount=rule['amount'],
                validUntil=rule['validUntil'], offers=[{key: deepcopy(o[key]) for key in
                ('offerId', 'productId', 'sellingPrice', 'unitBasis')} for o in campaign['proposal']['offers']]))
        return {'benefits': values}

    def member_offer_check(self, rule):
        if not rule or not rule.get('campaignId'):
            return False
        try:
            with self.repo.transaction() as rows:
                campaign = rows.get('campaign', rule['campaignId'])
                self.require_live(rows, campaign)
                return (campaign.get('memberOfferRuleId') == rule.get('memberOfferRuleId')
                        and rows.get('member_offer', rule['memberOfferRuleId']) == rule)
        except OperationsError as exc:
            if exc.code in {'CLOUD_UNAVAILABLE', 'TOOL_UNAVAILABLE'}:
                raise
            return False
        except (KeyError, TypeError):
            return False
