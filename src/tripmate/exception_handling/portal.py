"""Build supported recovery context from selected plans and explicit staff evidence.

A traveller report is never silently promoted to a supplier cancellation fact.
"""
from copy import deepcopy
from uuid import uuid4

from tripmate.operations.common import OperationsError, instant, safe_text
from .runtime import Referral, money


class PortalExceptionContexts:
    def __init__(self, operations):
        self.operations = operations

    def baseline(self, rec):
        plan_id = rec['fields'].get('planId')
        lifecycle = next((p for p in self.operations.trips(rec['case']['requesterId']) if p['planId'] == plan_id), None)
        if not lifecycle or not lifecycle.get('selectedVersionId'):
            raise Referral('MISSING_REQUIRED_FIELDS', 'An adopted Planning baseline is required for this investigation.')
        baseline = self.operations.planning_repository.get_version(lifecycle['selectedVersionId'])
        if (baseline['version']['travellerId'] != rec['case']['requesterId']
                or baseline['version']['planId'] != plan_id):
            raise OperationsError('ACCESS_DENIED', 'Affected itinerary ownership does not match.')
        return baseline, lifecycle

    def view(self, actor, case_id):
        rec = self.operations.repository.read('case', case_id)
        if (not rec or self.operations.profile(actor)['role'] != 'OPERATOR'
                or not self.operations.access.authorise(actor, 'REVIEW_CASE', rec['case'])
                or rec['case']['caseType'] not in {'DISRUPTION', 'COMPLAINT'}):
            raise OperationsError('ACCESS_DENIED', 'Only an authorised Operator can inspect investigation evidence.')
        try:
            baseline, lifecycle = self.baseline(rec)
            items = baseline['version']['items']
        except Referral:
            lifecycle, items = None, []
        return dict(evidence=self.operations.repository.read('exception_evidence', case_id),
                    items=items, lifecycle=lifecycle, simulationOnly=True)

    def record(self, actor, body):
        required = {'requestKey', 'caseId', 'revision', 'itemId', 'sourceReference', 'validUntil',
                    'sunkCost', 'confidence', 'restricted', 'legalConcern', 'safetyConcern', 'confirmed'}
        if (set(body) != required or body['confirmed'] is not True or type(body['restricted']) is not bool
                or any(type(body[k]) is not bool for k in ('legalConcern', 'safetyConcern'))
                or any(not isinstance(body[k], str) or not 1 <= len(body[k]) <= 100 for k in ('caseId', 'itemId', 'requestKey'))
                or type(body['revision']) is not int or body['revision'] < 1
                or not isinstance(body['confidence'], str) or body['confidence'] not in {'SUFFICIENT', 'LOW', 'UNKNOWN'}):
            raise OperationsError('INVALID_CONTRACT', 'Confirm complete structured cancellation evidence.')
        reference = safe_text(body['sourceReference'], 1000)
        try:
            money(body['sunkCost'])
            if instant(body['validUntil']) <= instant(self.operations.clock()):
                raise ValueError()
        except (ValueError, TypeError, AttributeError):
            raise OperationsError('INVALID_CONTRACT', 'Supply a future evidence validity and nonnegative AUD sunk cost.')
        def save(rows):
            rec = self.operations._owned(rows, actor, body['caseId'], 'REVIEW_CASE', body['revision'])
            if rec['case']['caseType'] != 'DISRUPTION' or rec['case']['status'] not in {'CONFIRMED', 'AWAITING_REQUESTER', 'HUMAN_ASSISTANCE'}:
                raise OperationsError('UNCONFIRMED_REQUEST', 'Record evidence before dispatching a confirmed disruption case.')
            baseline, lifecycle = self.baseline(rec)
            if lifecycle['planStatus'] != 'ACTIVE' or not any(i['itemId'] == body['itemId'] and i['productType'] == 'TRANSPORT'
                                                           for i in baseline['version']['items']):
                raise OperationsError('INVALID_CONTRACT', 'Choose a transport item in the current Active itinerary.')
            source = dict(sourceId='operator-notice-' + str(uuid4()), sourceType='FIXTURE',
                          sourceReference=reference, capturedAt=self.operations.clock(), freshness='FRESH', simulated=True)
            saved = dict(itemId=body['itemId'], source=source, validUntil=body['validUntil'], sunkCost=body['sunkCost'],
                         confidence=body['confidence'], restricted=body['restricted'], legalConcern=body['legalConcern'],
                         safetyConcern=body['safetyConcern'], recordedBy=actor,
                         baselineVersionId=baseline['version']['versionId'], confirmedRequest=rec['case']['confirmedRequest'])
            rows.put('exception_evidence', rec['id'], saved)
            if rec.get('exceptionRunId'):
                self.operations.specialists['exception'].invalidate_confirmation(rows, rec)
                rec.update(response=None, responseVersion=rec['responseVersion'] + 1, review=None, approvalId=None)
                rec.pop('specialistResult', None)
                rec['case']['status'] = 'AWAITING_REQUESTER'
                rec['case']['unresolvedQuestions'] = ['Investigation evidence changed. Re-confirm the request before a new investigation.']
            rec['revision'] += 1
            self.operations._event(rows, rec, 'TOOL_RESULT', 'Operator recorded a simulated cancellation notice: ' + source['sourceId'], actor=actor)
            self.operations._save(rows, rec)
            return dict(caseId=rec['id'], evidenceRecorded=True, simulationOnly=True)
        return self.operations._command(actor, 'exception-evidence', body['requestKey'], body, save)

    def ensure_current(self, snapshot):
        rec = self.operations.repository.read('case', snapshot['result']['caseId'])
        baseline, lifecycle = self.baseline(rec)
        notice = self.operations.repository.read('exception_evidence', rec['id'])
        if (lifecycle['planStatus'] != 'ACTIVE' or baseline['version']['versionId'] != snapshot['context']['itinerary']['versionId']
                or not notice or notice['source'] not in [e['source'] for e in snapshot['context']['evidence']]
                or not self.operations.access.authorise(notice['recordedBy'], 'REVIEW_CASE', rec['case'])):
            raise OperationsError('STALE_EVIDENCE', 'The active itinerary or trusted evidence changed; investigate a new proposal.')

    def load(self, case_id):
        rec = self.operations.repository.read('case', case_id)
        if rec is None:
            raise Referral('MISSING_REQUIRED_FIELDS', 'A confirmed Operations case is required.')
        baseline, lifecycle = self.baseline(rec)
        version = baseline['version']
        notice = self.operations.repository.read('exception_evidence', case_id)
        if rec['case']['caseType'] != 'DISRUPTION':
            raise Referral('MISSING_REQUIRED_FIELDS', 'Complaint evidence and an applicable policy need Operator confirmation; no liability is inferred.')
        if (not notice or notice['baselineVersionId'] != version['versionId']
                or notice['confirmedRequest'] != rec['case']['confirmedRequest']):
            raise Referral('MISSING_REQUIRED_FIELDS', 'An Operator must record cancellation evidence for this exact confirmed case and selected itinerary.')
        if self.operations.profile(notice['recordedBy'])['role'] != 'OPERATOR':
            raise Referral('MISSING_REQUIRED_FIELDS', 'The evidence author is no longer an authorised Operator.')
        request = deepcopy(baseline['request'])
        request.update(caseId=case_id, correlationId=rec['case']['correlationId'], requestId=str(uuid4()),
                       baselineVersionId=version['versionId'], confirmedAt=rec['case']['confirmedAt'], confirmedChangedFields=[])
        sources = {s['sourceId']: deepcopy(s) for s in version['sourceReferences']}
        evidence = [dict(source=s, validUntil=notice['validUntil'], assertions=[],
                         note='Recorded baseline facts only; not a fresh availability or refund claim.') for s in sources.values()]
        evidence.append(dict(source=notice['source'], validUntil=notice['validUntil'],
                             assertions=[dict(key=notice['itemId'] + ':status', value='CANCELLED')],
                             note='Explicit Operator-confirmed simulated cancellation notice.'))
        items = [dict(itemId=i['itemId'], kind={'TRANSPORT': 'TRANSPORT', 'ACCOMMODATION': 'HOTEL', 'ACTIVITY': 'ACTIVITY'}[i['productType']],
                      origin=i['origin'], destination=i['destination'], startAt=i['startAt'], endAt=i['endAt'],
                      remainingCost=i['quotedPrice']['amount'], sourceIds=deepcopy(i['sourceIds'])) for i in version['items']]
        return dict(contextVersion='exception-fixture-1', caseId=case_id, travellerId=rec['case']['requesterId'],
                    simulationOnly=True, assessedAt=self.operations.clock(),
                    issue=dict(kind='DISRUPTION', itemId=notice['itemId'], summary=rec['fields']['details'],
                               confidence=notice['confidence'], legalConcern=notice['legalConcern'], safetyConcern=notice['safetyConcern'],
                               requestedActions=['BINDING_COMMITMENT'] if notice['restricted'] else []),
                    itinerary=dict(versionId=version['versionId'], materialVersion=version['versionNo'],
                                   travellerId=version['travellerId'], planStatus=lifecycle['planStatus'], sunkCost=notice['sunkCost'], items=items),
                    constraints=[], evidence=evidence, supplierOffers=[], policies=[],
                    planningContext=dict(request=request, spec=deepcopy(baseline['spec']), baseline=baseline))
