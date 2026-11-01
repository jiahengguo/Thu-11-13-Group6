"""Authenticated four-agent recovery, trusted evidence, privacy and durable import."""
import unittest
from copy import deepcopy
from unittest.mock import patch
from uuid import uuid4

import test_planning_portal as planning_tests
from tripmate.fixtures.b03 import FIXTURE_TIME
from tripmate.portal.server import Portal
from tripmate.portal.repository import CloudRecords


class ExceptionPortalTests(unittest.TestCase):
    def setUp(self):
        self.fixture = planning_tests.PlanningPortalTests()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.setUp()
        self.f = self.fixture
        self.clock = patch('tripmate.exception_handling.runtime.now', return_value=FIXTURE_TIME)
        self.clock.start()
        self.addCleanup(self.clock.stop)
        cid, ids, result = self.f.generate()
        self.f.release(cid, result['revision'])
        self.f.adopt(ids[0])
        self.f.post(self.f.traveller, 'start-trip', dict(versionId=ids[0], confirmed=True))
        self.baseline = self.f.app.planning.get_version(ids[0])
        self.cid = self.f.confirm(self.f.traveller, 'DISRUPTION', dict(
            planId=self.baseline['version']['planId'], details='Please investigate the simulated cancelled transport.'))

    def evidence(self, **changes):
        version = self.f.clients[self.f.operator].call('/api/operations/case?caseId=' + self.cid)[1]['revision']
        item = next(i for i in self.baseline['version']['items'] if i['productType'] == 'TRANSPORT')
        body = dict(requestKey=str(uuid4()), caseId=self.cid, revision=version, itemId=item['itemId'],
                    sourceReference='synthetic://supplier/cancellation-notice', validUntil='2026-11-01T00:00:00+11:00',
                    sunkCost='0.00', confidence='SUFFICIENT', restricted=False, legalConcern=False, safetyConcern=False, confirmed=True)
        body.update(changes)
        return body

    def record(self, **changes):
        body = self.evidence(**changes)
        result = self.f.clients[self.f.operator].call('/api/exception/evidence', body)
        self.assertEqual(result[0], 200, result[1])
        return body

    def dispatch(self):
        version = self.f.clients[self.f.traveller].call('/api/operations/case?caseId=' + self.cid)[1]['revision']
        return self.f.post(self.f.traveller, 'dispatch', dict(caseId=self.cid, revision=version))

    def test_recovery_uses_current_project_ports_review_delivery_selection_and_restart(self):
        self.assertIs(self.f.app.exception.runtime.reviewer, self.f.app.reviewer)
        self.assertIs(self.f.app.campaigns.reviewer, self.f.app.reviewer)
        self.assertIs(self.f.app.supplier.reviewer, self.f.app.reviewer)
        self.assertEqual(set(self.f.app.reviewer.validators),
                         {'SupplierOffer', 'ItineraryVersion', 'RecoveryProposal',
                          'ResolutionRecommendation', 'CampaignProposal'})
        supplier_record = self.f.app.supplier.repository.records()[0]
        offer = supplier_record['offer']
        proposal = dict(deepcopy(offer), price=deepcopy(supplier_record['price']))
        evidence = deepcopy(offer['sourceReferences'])
        policy = [{'policyVersion': self.f.app.supplier.policy.version}]
        self.assertEqual(self.f.app.reviewer.review(proposal, evidence, policy)['outcome'], 'PASS')
        proposal['price']['sellingPrice']['amount'] = '1.00'
        self.assertEqual(self.f.app.reviewer.review(proposal, evidence, policy)['outcome'], 'REVISION_REQUIRED')
        self.record()
        view = self.dispatch()
        self.assertEqual(view['case']['status'], 'UNDER_REVIEW', view)
        internal = self.f.app.operations.repository.read('case', self.cid)
        investigation = self.f.app.exception.investigation(self.f.operator, self.cid)
        self.assertEqual(investigation['dependencies']['supplier'], 'ProjectSupplier')
        self.assertEqual(investigation['dependencies']['planning'], 'ProjectPlanning')
        self.assertEqual(investigation['result']['review']['policyVersion'], 'shared-deterministic-review-1')
        self.assertNotIn('recoveryOptions', view)
        self.assertIsNone(view['response'])
        presented = self.f.release(self.cid, view['revision'])
        self.assertEqual(presented['case']['status'], 'AWAITING_REQUESTER')
        self.assertTrue(presented['canSelectRecovery'])
        public = presented['recoveryOptions']
        self.assertTrue(public['options'])
        self.assertNotIn('planningRecord', str(public))
        self.assertNotIn('supplierCost', str(public))
        chosen = self.f.post(self.f.traveller, 'exception-selection', dict(caseId=self.cid, revision=presented['revision'],
                    runId=public['runId'], optionId=public['options'][0]['offerId'], confirmed=True))
        self.assertEqual(chosen['case']['status'], 'UNDER_REVIEW')
        final = self.f.release(self.cid, chosen['revision'])
        self.assertEqual(final['case']['status'], 'AWAITING_REQUESTER')
        self.assertFalse(final['canSelectRecovery'])
        self.assertEqual(self.f.app.planning.get_version(self.baseline['version']['versionId']), self.baseline)
        restarted = Portal(self.f.cloud, supplier_policy=self.f.policy)
        self.assertEqual(restarted.exception.investigation(self.f.operator, self.cid)['result'], internal['specialistResult'])
        traces = self.f.app.operations.traces(self.f.operator, self.cid)
        self.assertEqual(len(traces), len({e['eventId'] for e in traces}))
        self.assertTrue({'operations', 'exception', 'supplier', 'planning'} <=
                        {e['actor'] for e in traces})
        supplier_trace = next(e for e in traces if e['actor'] == 'supplier')
        planning_trace = next(e for e in traces if e['actor'] == 'planning')
        self.assertEqual(supplier_trace['runId'], planning_trace['runId'])
        self.assertEqual(supplier_trace['caseId'], planning_trace['caseId'])
        self.assertLess(traces.index(supplier_trace), traces.index(planning_trace))

    def test_requester_report_cannot_be_used_as_a_supplier_cancellation_fact(self):
        view = self.dispatch()
        self.assertEqual(view['case']['status'], 'AWAITING_REQUESTER')
        self.assertIsNone(view['response'])
        self.assertNotIn('recoveryOptions', view)
        self.assertIsNone(self.f.app.exception.investigation(self.f.operator, self.cid)['proposal'])

    def test_only_operator_can_record_or_read_investigation_and_stale_revision_is_rejected(self):
        body = self.evidence()
        for actor in (self.f.traveller, self.f.other, self.f.supplier):
            self.assertEqual(self.f.clients[actor].call('/api/exception/evidence', body)[0], 403)
            self.assertEqual(self.f.clients[actor].call('/api/exception/investigation?caseId=' + self.cid)[0], 403)
        saved = self.record()
        self.assertEqual(self.f.clients[self.f.operator].call('/api/exception/evidence', saved)[0], 200)
        saved['requestKey'] = str(uuid4())
        self.assertEqual(self.f.clients[self.f.operator].call('/api/exception/evidence', saved)[0], 409)

    def test_restricted_recovery_has_separate_proposal_and_response_decisions(self):
        self.record(restricted=True)
        pending = self.dispatch()
        self.assertEqual(pending['case']['status'], 'AWAITING_HUMAN_APPROVAL', pending)
        decided = self.f.post(self.f.operator, 'review', dict(caseId=self.cid, revision=pending['revision'],
                              decision='APPROVE', reason='Approve only this simulated proposal.'))
        self.assertEqual(decided['case']['status'], 'UNDER_REVIEW')
        self.assertIsNone(self.f.clients[self.f.traveller].call('/api/operations/case?caseId=' + self.cid)[1]['response'])
        public = self.f.release(self.cid, decided['revision'])
        self.assertTrue(public['recoveryOptions']['options'])
        self.assertTrue(self.f.app.operations.repository.list('exception_approval'))
        self.assertTrue(self.f.app.operations.repository.list('approval'))

    def test_safety_notice_never_presents_success(self):
        self.record(safetyConcern=True)
        view = self.dispatch()
        self.assertEqual(view['case']['status'], 'HUMAN_ASSISTANCE')
        self.assertIsNone(view['response'])
        self.assertNotIn('recoveryOptions', view)

    def test_cloud_savepoint_removes_partial_specialist_import(self):
        rows = CloudRecords(dict(records=[]))
        rows.put('unrelated', 'keep', {'saved': True})
        with self.assertRaises(RuntimeError):
            with rows.savepoint():
                rows.put('exception_run', 'partial', {'invalid': True})
                rows.events.append({'partial': True})
                raise RuntimeError('Controlled receipt failure')
        self.assertIsNone(rows.get('exception_run', 'partial'))
        self.assertEqual(rows.get('unrelated', 'keep'), {'saved': True})
        self.assertEqual(rows.events, [])

    def test_low_confidence_and_expired_evidence_never_present_recovery(self):
        self.record(confidence='LOW')
        view = self.dispatch()
        self.assertEqual(view['case']['status'], 'HUMAN_ASSISTANCE')
        self.assertIsNone(view['response'])

    def test_expired_notice_cannot_be_recorded_or_released(self):
        body = self.evidence(validUntil='2026-10-01T00:00:00+11:00')
        self.assertEqual(self.f.clients[self.f.operator].call('/api/exception/evidence', body)[0], 422)
        self.record()
        self.f.app.operations.clock = lambda: '2026-11-02T00:00:00+11:00'
        view = self.dispatch()
        self.assertEqual(view['case']['status'], 'AWAITING_REQUESTER')
        self.assertNotIn('recoveryOptions', view)

    def test_failed_snapshot_save_and_partial_import_never_release_a_proposal(self):
        self.record()
        original = CloudRecords.put
        def reject_import(rows, kind, key, payload):
            if kind == 'exception_run':
                raise ValueError('Controlled import failure')
            return original(rows, kind, key, payload)
        with patch.object(CloudRecords, 'put', reject_import):
            view = self.dispatch()
        self.assertEqual(view['case']['status'], 'HUMAN_ASSISTANCE')
        self.assertIsNone(view['response'])
        self.assertEqual(self.f.app.operations.repository.list('exception_run'), [])
        self.assertFalse(any(e['actor'] == 'exception' for e in self.f.app.operations.repository.find_by_case(self.cid)))
        # Internal saved attempts may exist, but a failed receipt cannot publish them.
        self.assertTrue(self.f.app.operations.repository.list('exception_saved_run'))

    def test_no_eligible_alternative_retains_open_case_and_baseline(self):
        self.record()
        with self.f.app.operations.repository.transaction() as rows:
            for pointer in rows.all('supplier_current'):
                current = self.f.app.supplier.repository.current(pointer['offerId'])
                if current['product']['role'] == 'OUTBOUND':
                    rows.put('supplier_current', pointer['offerId'], dict(pointer, invalidated=True))
        view = self.dispatch()
        self.assertEqual(view['case']['status'], 'HUMAN_ASSISTANCE')
        self.assertIsNone(view['response'])
        self.assertEqual(self.f.app.planning.get_version(self.baseline['version']['versionId']), self.baseline)
        investigation = self.f.app.exception.investigation(self.f.operator, self.cid)
        self.assertEqual(investigation['result']['errors'][0]['code'], 'NO_FEASIBLE_ITINERARY')
        traces = self.f.app.operations.traces(self.f.operator, self.cid)
        self.assertTrue({'supplier', 'planning'} <= {e['actor'] for e in traces})

    def test_changed_notice_revokes_presented_options_until_confirmed_reinvestigation(self):
        self.record()
        view = self.dispatch()
        presented = self.f.release(self.cid, view['revision'])
        old = presented['recoveryOptions']
        self.record(sourceReference='synthetic://supplier/updated-notice')
        changed = self.f.clients[self.f.traveller].call('/api/operations/case?caseId=' + self.cid)[1]
        self.assertIsNone(changed['response'])
        self.assertNotIn('recoveryOptions', changed)
        body = dict(requestKey=str(uuid4()), caseId=self.cid, revision=changed['revision'], runId=old['runId'],
                    optionId=old['options'][0]['offerId'], confirmed=True)
        self.assertNotEqual(self.f.clients[self.f.traveller].call('/api/operations/exception-selection', body)[0], 200)
        confirmed = self.f.post(self.f.traveller, 'clarify', dict(caseId=self.cid, revision=changed['revision'],
                intents=[dict(caseType='DISRUPTION', fields=changed['fields'])], confirmed=True))
        renewed = self.dispatch()
        self.assertEqual(renewed['case']['status'], 'UNDER_REVIEW')
        saved = self.f.app.exception.investigation(self.f.operator, self.cid)
        self.assertEqual(saved['proposal']['subject']['materialVersion'], 2)

    def test_snapshot_persistence_failure_cannot_return_a_successful_handoff(self):
        self.record()
        with patch.object(self.f.app.exception.runtime.repository, 'save', side_effect=OSError('Controlled save failure')):
            view = self.dispatch()
        self.assertEqual(view['case']['status'], 'HUMAN_ASSISTANCE')
        self.assertIsNone(view['response'])
        self.assertEqual(self.f.app.operations.repository.list('exception_run'), [])

    def lifecycle_call(self, actor, operation, current, **fields):
        return self.f.clients[actor].call('/api/operations/' + operation, dict(
            requestKey=str(uuid4()), caseId=self.cid, revision=current['revision'], **fields))

    def operator_view(self):
        status, view, _ = self.f.clients[self.f.operator].call('/api/operations/case?caseId=' + self.cid)
        self.assertEqual(status, 200, view)
        return view

    def assert_unresolved_closure(self, current, reason):
        response = self.lifecycle_call(self.f.operator, 'case-action', current,
            action='CLOSE_CASE', reason=reason)
        self.assertEqual(response[0], 200, response[1])
        closed = self.operator_view()
        self.assertEqual(closed['case']['status'], 'CLOSED')
        self.assertEqual(closed['exception']['exceptionStage'], 'CLOSED_UNRESOLVED')
        self.assertEqual(self.f.app.planning.get_version(self.baseline['version']['versionId']), self.baseline)
        events = self.f.app.operations.traces(self.f.operator, self.cid)
        self.assertTrue(any(e['eventType'] == 'CASE_CLOSED' and reason in e['summary'] for e in events))
        return closed

    def test_decline_through_authenticated_portal_keeps_case_unresolved(self):
        self.record()
        presented = self.f.release(self.cid, self.dispatch()['revision'])
        denied = self.lifecycle_call(self.f.operator, 'case-action', presented,
            action='CLOSE_CASE', reason='A waiting traveller decision is not a resolved outcome.')
        self.assertEqual(denied[0], 409)
        declined = self.lifecycle_call(self.f.traveller, 'exception-selection', presented,
            runId=presented['recoveryOptions']['runId'], optionId=None, confirmed=True)
        self.assertEqual(declined[0], 200, declined[1])
        current = self.operator_view()
        self.assertEqual(current['case']['status'], 'HUMAN_ASSISTANCE')
        self.assertEqual(current['exception']['exceptionStage'], 'HUMAN_TAKEOVER')
        self.assertFalse(declined[1]['canSelectRecovery'])
        forbidden = self.lifecycle_call(self.f.traveller, 'case-action', current,
            action='CLOSE_CASE', reason='Traveller cannot close this recovery case.')
        self.assertEqual(forbidden[0], 403)
        empty = self.lifecycle_call(self.f.operator, 'case-action', current, action='CLOSE_CASE', reason='')
        self.assertEqual(empty[0], 422)
        self.assert_unresolved_closure(current, 'Traveller declined all options; closed unresolved for manual handling. No travel change was executed.')

    def test_no_response_uses_explicit_operator_takeover_without_invented_deadline(self):
        self.record()
        presented = self.f.release(self.cid, self.dispatch()['revision'])
        before = self.operator_view()
        self.assertEqual(before['exception']['exceptionStage'], 'AWAITING_TRAVELLER_DECISION')
        # Reopening/restarting is not a timeout, reminder or inferred traveller decision.
        restarted = Portal(self.f.cloud, supplier_policy=self.f.policy)
        self.assertEqual(restarted.operations.case_view(self.f.operator, self.cid)['revision'], before['revision'])
        denied = self.lifecycle_call(self.f.operator, 'case-action', presented,
            action='CLOSE_CASE', reason='No automatic closure merely because a response is missing.')
        self.assertEqual(denied[0], 409)
        taken = self.lifecycle_call(self.f.operator, 'review', before,
            decision='TAKE_OVER', reason='No traveller response has been recorded; operator explicitly takes over.')
        self.assertEqual(taken[0], 200, taken[1])
        current = self.operator_view()
        self.assertEqual(current['case']['status'], 'HUMAN_ASSISTANCE')
        self.assertEqual(current['exception']['exceptionStage'], 'HUMAN_TAKEOVER')
        self.assert_unresolved_closure(current, 'Operator recorded the manual handoff; closed unresolved, with no confirmed booking or trip recovery.')

    def test_pending_recovery_cannot_be_selected_or_closed_before_human_decision(self):
        self.record(restricted=True)
        pending = self.dispatch()
        self.assertEqual(pending['case']['status'], 'AWAITING_HUMAN_APPROVAL')
        self.assertIsNone(pending['response'])
        current = self.operator_view()
        attempted = self.lifecycle_call(self.f.traveller, 'exception-selection', pending,
            runId=current['exception']['exceptionRunId'], optionId=None, confirmed=True)
        self.assertEqual(attempted[0], 409)
        denied = self.lifecycle_call(self.f.operator, 'case-action', current,
            action='CLOSE_CASE', reason='An undecided restricted proposal is not a closure outcome.')
        self.assertEqual(denied[0], 409)
        self.assertEqual(self.operator_view()['case']['status'], 'AWAITING_HUMAN_APPROVAL')
        rejected = self.lifecycle_call(self.f.operator, 'review', current,
            decision='REJECT', reason='Operator rejects the exact restricted recovery proposal.')
        self.assertEqual(rejected[0], 200, rejected[1])
        current = self.operator_view()
        self.assertEqual(current['exception']['exceptionStage'], 'HUMAN_TAKEOVER')
        self.assert_unresolved_closure(current, 'Rejected proposal referred for manual handling; no external action completed.')

    def test_selection_requires_followup_delivery_before_reasoned_unresolved_closure(self):
        self.record()
        presented = self.f.release(self.cid, self.dispatch()['revision'])
        selected = self.lifecycle_call(self.f.traveller, 'exception-selection', presented,
            runId=presented['recoveryOptions']['runId'],
            optionId=presented['recoveryOptions']['options'][0]['offerId'], confirmed=True)
        self.assertEqual(selected[0], 200, selected[1])
        self.assertEqual(selected[1]['case']['status'], 'UNDER_REVIEW')
        denied = self.lifecycle_call(self.f.operator, 'case-action', selected[1],
            action='CLOSE_CASE', reason='The selected recommendation has not completed response review and delivery.')
        self.assertEqual(denied[0], 409)
        delivered = self.f.release(self.cid, selected[1]['revision'])
        self.assertEqual(delivered['case']['status'], 'AWAITING_REQUESTER')
        self.assertEqual(self.operator_view()['exception']['exceptionStage'], 'RECOMMENDATION_DELIVERED')
        self.assert_unresolved_closure(delivered, 'Checked recommendation delivered; case closed unresolved with manual follow-up, not a completed rebooking.')
