"""Synthetic examples, not project-wide commercial policies or real approvals."""
from copy import deepcopy
from .ports import MemoryContext, SimulatedSupplier, SimulatedPlanning, SimulatedReviewer
from .runtime import ExceptionRuntime

SCENARIOS = ('normal', 'conflict', 'missing-evidence', 'no-alternative', 'low-confidence',
             'safety', 'approval', 'dependency-unavailable', 'review-failed')

def fixture(kind='DISRUPTION', scenario='normal'):
    if kind not in {'DISRUPTION', 'COMPLAINT'} or scenario not in SCENARIOS:
        raise ValueError('Unsupported demonstration selection')
    cid = 'exc-demo-' + kind.lower()
    at = '2026-10-20T08:00:00+11:00' if kind == 'DISRUPTION' else '2026-10-20T16:00:00+11:00'
    def source(sid):
        return dict(sourceId=sid, sourceType='FIXTURE', sourceReference='fixture://exception/v1/' + sid,
                    capturedAt='2026-10-20T07:30:00+11:00', freshness='FRESH', simulated=True)
    def evidence(sid, assertions, note):
        return dict(source=source(sid), validUntil='2026-10-21T00:00:00+11:00',
                    assertions=[dict(key=k, value=v) for k, v in assertions.items()], note=note)
    def item(iid, kind, start, end, cost, origin, destination, sid):
        return dict(itemId=iid, kind=kind, startAt=start, endAt=end, remainingCost=cost,
                    origin=origin, destination=destination, sourceIds=[sid])
    flight = item('flight-original', 'FLIGHT', '2026-10-20T09:00:00+11:00', '2026-10-20T10:30:00+11:00',
                  '0.00', 'SYD', 'MEL', 'itinerary')
    stay = item('hotel', 'HOTEL', '2026-10-20T15:00:00+11:00', '2026-10-22T10:00:00+11:00',
                '240.00', 'MEL', 'MEL', 'itinerary')
    activity = item('activity', 'ACTIVITY', '2026-10-21T11:00:00+11:00', '2026-10-21T13:00:00+11:00',
                    '40.00', 'MEL', 'MEL', 'itinerary')
    replacement = item('flight-replacement', 'FLIGHT', '2026-10-20T10:00:00+11:00', '2026-10-20T11:30:00+11:00',
                       '220.00', 'SYD', 'MEL', 'supplier')
    offer = dict(offerId='replacement-early', status='APPROVED', available=True,
                 validUntil='2026-10-20T09:30:00+11:00', sourceIds=['supplier'], replacement=replacement,
                 terms='Synthetic quotation only. No reservation or payment. Availability must be rechecked on real integration.')
    late = deepcopy(offer)
    late['offerId'] = 'replacement-late'
    late['replacement'].update(itemId='flight-late', startAt='2026-10-20T16:00:00+11:00', endAt='2026-10-20T17:30:00+11:00')
    case = dict(schemaVersion='1.0.0', caseId=cid, correlationId=cid + '-correlation',
                sourceReferences=[source('operations-confirmation')], validationResults=[], errors=[], requiresApproval=False,
                caseKind='CUSTOMER', caseType=kind, externalRequestId=cid + '-request', requesterId='synthetic-traveller',
                requesterType='TRAVELLER', confirmedAt='2026-10-20T07:45:00+11:00', createdAt='2026-10-20T07:40:00+11:00',
                status='CONFIRMED', coordinator='operations', primaryHandler='exception', relatedCaseIds=[], humanRequestCount=0,
                confirmedRequest='Investigate the confirmed ' + kind.lower() + ' for flight-original.',
                unresolvedQuestions=[], entitlementDecision=None)
    ev = [evidence('itinerary', {}, 'Confirmed synthetic itinerary and price basis: AUD 180 already paid and non-refundable; remaining hotel AUD 240 and activity AUD 40.'),
          evidence('supplier', {}, 'Synthetic approved replacement flight: AUD 220; late alternative fails timing.'),
          evidence('cancellation', {'flight-original:status': 'CANCELLED'}, 'Simulated supplier cancellation notice.'),
          evidence('service-schedule', {'flight-original:scheduledArrival': '2026-10-20T10:30:00+11:00'}, 'Scheduled service record.'),
          evidence('service-actual', {'flight-original:actualArrival': '2026-10-20T12:00:00+11:00'}, 'Observed arrival service record.'),
          evidence('policy', {'policy:delay-demo:version': '1', 'policy:delay-demo:action': 'EXPLAIN_AND_APOLOGISE'}, 'Demonstration policy: explain a documented delay and offer an apology; financial decisions require a human.')]
    if kind == 'DISRUPTION':
        ev = ev[:3]
    else:
        ev = [ev[0]] + ev[3:]
        ev[2]['source']['capturedAt'] = '2026-10-20T12:05:00+11:00'
        case.update(createdAt='2026-10-20T15:00:00+11:00', confirmedAt='2026-10-20T15:05:00+11:00')
    ctx = dict(contextVersion='exception-fixture-1', caseId=cid, travellerId=case['requesterId'], simulationOnly=True,
               assessedAt=at, issue=dict(kind=kind, itemId='flight-original', summary=case['confirmedRequest'],
               confidence='SUFFICIENT', legalConcern=False, safetyConcern=False, requestedActions=[]),
               itinerary=dict(versionId='baseline-1', materialVersion=1, travellerId=case['requesterId'],
                              planStatus='ACTIVE', sunkCost='180.00', items=[flight, stay, activity]),
               constraints=[dict(name='budgetTotal', value='800.00'),
                            dict(name='minTransferMinutes', value='60'),
                            dict(name='earliestDeparture', value='2026-10-20T09:00:00+11:00'),
                            dict(name='latestArrival', value='2026-10-20T14:00:00+11:00')],
               evidence=ev, supplierOffers=[offer, late] if kind == 'DISRUPTION' else [],
               policies=[] if kind == 'DISRUPTION' else [dict(policyId='delay-demo', version='1', sourceIds=['policy'],
                           action='EXPLAIN_AND_APOLOGISE', description='Explain documented delay and offer an apology. No financial entitlement inferred.')])
    if scenario == 'conflict':
        key = 'flight-original:status' if kind == 'DISRUPTION' else 'flight-original:actualArrival'
        val = 'ON_TIME' if kind == 'DISRUPTION' else '2026-10-20T10:30:00+11:00'
        ctx['evidence'].append(evidence('contradictory-record', {key: val}, 'Deliberately conflicting simulated record.'))
    if scenario == 'missing-evidence':
        ctx['evidence'] = [e for e in ev if e['source']['sourceId'] not in {'cancellation', 'service-actual'}]
    if scenario == 'no-alternative':
        ctx['supplierOffers'] = []
        if kind == 'COMPLAINT':
            ctx['policies'] = []
    if scenario == 'low-confidence':
        ctx['issue']['confidence'] = 'LOW'
    if scenario == 'safety':
        ctx['issue']['safetyConcern'] = True
    if scenario == 'approval':
        ctx['issue']['requestedActions'] = ['BINDING_COMMITMENT'] if kind == 'DISRUPTION' else ['REFUND']
        if kind == 'COMPLAINT':
            ctx['policies'][0]['action'] = 'HUMAN_REVIEW_REFUND'
            for e in ctx['evidence']:
                if e['source']['sourceId'] == 'policy':
                    for a in e['assertions']:
                        if a['key'] == 'policy:delay-demo:action':
                            a['value'] = 'HUMAN_REVIEW_REFUND'
    return case, ctx

class UnavailableContext:
    def load(self, case_id):
        raise OSError('Simulated unavailable dependency')

class RejectingReviewer(SimulatedReviewer):
    def review(self, subject, evidence, policies):
        result = super().review(subject, evidence, policies)
        result.update(outcome='REVISION_REQUIRED', reasons=['Simulated reviewer requests clarification.'])
        return result

def demo_runtime(repository, kind='DISRUPTION', scenario='normal'):
    case, context = fixture(kind, scenario)
    contexts = UnavailableContext() if scenario == 'dependency-unavailable' else MemoryContext({case['caseId']: context})
    reviewer = RejectingReviewer() if scenario == 'review-failed' else SimulatedReviewer()
    return case, ExceptionRuntime(contexts, repository, SimulatedSupplier(), SimulatedPlanning(), reviewer)
