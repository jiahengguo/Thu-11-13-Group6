"""Real Operations dispatch/review/storage code on explicitly synthetic evidence."""
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from tripmate.fixtures import FixtureRepository
from tripmate.operations import OperationsService, OperationsRepository
from tripmate.operations.common import OperationsError
from tripmate.operations.repository import Records
from tripmate.exception_handling import ExceptionRepository
from tripmate.exception_handling.fixtures import fixture
from tripmate.exception_handling.ports import MemoryContext, SimulatedSupplier, SimulatedPlanning, SimulatedReviewer
from tripmate.exception_handling.integration import connect_exception

PAID, OTHER, OPERATOR = 'traveller:paid', 'traveller:free', 'operator:fixture'
TIME = '2026-10-20T08:00:00+11:00'


class ExceptionIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        path = Path(self.tmp.name) / 'shared.sqlite3'
        self.fixtures = FixtureRepository(path)
        self.fixtures.ensure_seeded()
        self.repo = OperationsRepository(path)
        self.service = OperationsService(self.repo, self.fixtures, clock=lambda: TIME)
        self.exceptions = ExceptionRepository(path)
        self.contexts = MemoryContext({})
        self.bridge = connect_exception(self.service, self.contexts, self.exceptions,
                                        SimulatedSupplier(), SimulatedPlanning())
        self.seq = 0

    def key(self):
        self.seq += 1
        return 'exception-action-' + str(self.seq)

    def case(self, scenario='normal'):
        intents = [{'caseType': 'DISRUPTION', 'fields': {
            'planId': 'itinerary:active-paid', 'details': 'Confirmed synthetic flight cancellation.'}}]
        intake = self.service.intake(PAID, self.key(), 'Flight cancelled', intents)
        case_id = self.service.confirm(PAID, self.key(), intake['id'], 1, intents, True)['caseIds'][0]
        _, context = fixture('DISRUPTION', scenario)
        context.update(caseId=case_id, travellerId=PAID)
        context['itinerary']['travellerId'] = PAID
        self.contexts.contexts[case_id] = context
        return self.service.case_view(PAID, case_id)

    def dispatch(self, view, key=None):
        return self.service.dispatch(PAID, key or self.key(), view['case']['caseId'], view['revision'])

    def review(self, view, decision='APPROVE', actor=OPERATOR):
        return self.service.review_case(actor, self.key(), view['case']['caseId'], view['revision'], decision, 'Reviewed exact version')

    def test_shared_snapshot_trace_reopen_privacy_and_duplicate_dispatch(self):
        view = self.case()
        key = self.key()
        result = self.dispatch(view, key)
        self.assertEqual(result['case']['status'], 'UNDER_REVIEW')
        self.assertIsNone(result['response'])
        rec = self.repo.read('case', view['case']['caseId'])
        snapshot = self.bridge.investigation(OPERATOR, rec['id'])
        self.assertEqual(snapshot['result'], rec['specialistResult'])
        self.assertTrue(any(e['actor'] == 'exception' for e in self.repo.find_by_case(rec['id'])))
        self.assertEqual(OperationsRepository(self.repo.path).read('exception_run', rec['exceptionRunId']), snapshot)
        self.dispatch(view, key)
        self.assertEqual(len(self.exceptions.recent()), 1)
        for actor in (PAID, OTHER):
            with self.assertRaises(OperationsError):
                self.bridge.investigation(actor, rec['id'])

    def test_pending_proposal_and_response_require_separate_scoped_decisions(self):
        view = self.dispatch(self.case('approval'))
        self.assertEqual(view['case']['status'], 'AWAITING_HUMAN_APPROVAL')
        op = self.service.case_view(OPERATOR, view['case']['caseId'])
        self.assertTrue(op['exception']['exceptionApprovalId'])
        with self.assertRaises(OperationsError):
            self.review(view, actor=PAID)
        view = self.review(view)
        self.assertEqual(view['case']['status'], 'UNDER_REVIEW')
        with self.assertRaises(OperationsError):
            self.service.deliver(OPERATOR, self.key(), view['case']['caseId'], view['revision'])
        view = self.review(view)
        self.assertEqual(view['case']['status'], 'READY_TO_RESPOND')
        view = self.service.deliver(OPERATOR, self.key(), view['case']['caseId'], view['revision'])
        self.assertTrue(view['delivered'])
        self.assertEqual(self.repo.read('case', view['caseId'])['case']['status'], 'AWAITING_REQUESTER')
        decisions = self.repo.list('exception_approval')
        self.assertEqual(sorted(a['status'] for a in decisions), ['DECIDED', 'PENDING'])
        response_approvals = self.repo.list('approval')
        self.assertTrue(response_approvals)
        self.assertTrue(all(a['subject']['subjectType'] == 'Case' for a in response_approvals))

    def present(self, view):
        view = self.review(view)
        self.service.deliver(OPERATOR, self.key(), view['case']['caseId'], view['revision'])
        return self.service.case_view(PAID, view['case']['caseId'])

    def test_present_select_review_deliver_and_authorised_unresolved_closure(self):
        view = self.dispatch(self.case())
        self.assertNotIn('recoveryOptions', view)
        view = self.present(view)
        options = view['recoveryOptions']
        self.assertEqual(view['case']['status'], 'AWAITING_REQUESTER')
        args = (view['case']['caseId'], view['revision'], options['runId'], options['options'][0]['offerId'])
        with self.assertRaises(OperationsError):
            self.service.select_exception(PAID, self.key(), *args, False)
        with self.assertRaises(OperationsError):
            self.service.select_exception(OTHER, self.key(), *args, True)
        view = self.service.select_exception(PAID, self.key(), *args, True)
        self.assertEqual(view['case']['status'], 'UNDER_REVIEW')
        view = self.present(view)
        op = self.service.case_view(OPERATOR, view['case']['caseId'])
        self.assertEqual(op['exception']['exceptionStage'], 'RECOMMENDATION_DELIVERED')
        with self.assertRaises(OperationsError):
            self.service.case_action(PAID, self.key(), view['case']['caseId'], view['revision'], 'CLOSE_CASE', 'Close')
        view = self.service.case_action(OPERATOR, self.key(), view['case']['caseId'], view['revision'],
                                        'CLOSE_CASE', 'Recommendation delivered; booking remains unchanged, manual handling recorded.')
        self.assertEqual(view['case']['status'], 'CLOSED')
        self.assertEqual(view['exception']['exceptionStage'], 'CLOSED_UNRESOLVED')

    def test_declining_presented_options_escalates_without_closing(self):
        view = self.present(self.dispatch(self.case()))
        view = self.service.select_exception(PAID, self.key(), view['case']['caseId'], view['revision'],
                                              view['recoveryOptions']['runId'], None, True)
        self.assertEqual(view['case']['status'], 'HUMAN_ASSISTANCE')

    def test_reject_takeover_and_request_revision_preserve_case_and_evidence(self):
        for decision, state in [('REJECT', 'HUMAN_ASSISTANCE'), ('TAKE_OVER', 'HUMAN_ASSISTANCE'),
                                ('REQUEST_REVISION', 'AWAITING_REQUESTER')]:
            view = self.review(self.dispatch(self.case('approval')), decision)
            self.assertEqual(view['case']['status'], state)
            self.assertIsNotNone(self.bridge.investigation(OPERATOR, view['case']['caseId']))
            with self.assertRaises(OperationsError):
                self.service.deliver(OPERATOR, self.key(), view['case']['caseId'], view['revision'])

    def test_stale_evidence_cannot_be_approved_or_released(self):
        view = self.dispatch(self.case('approval'))
        self.service.clock = lambda: '2026-10-21T10:00:00+11:00'
        with self.assertRaises(OperationsError):
            self.review(view)
        self.assertEqual(self.repo.read('case', view['case']['caseId'])['case']['status'], 'AWAITING_HUMAN_APPROVAL')

    def test_forged_or_superseded_proposal_decision_cannot_release(self):
        view = self.review(self.dispatch(self.case('approval')))
        rec = self.repo.read('case', view['case']['caseId'])
        with self.repo.transaction() as rows:
            decision = rows.get('exception_approval', rec['exceptionDecisionId'])
            decision['subject']['materialVersion'] += 1
            rows.put('exception_approval', decision['approvalId'], decision)
        with self.assertRaises(OperationsError):
            self.review(view)

    def test_import_failure_rolls_back_all_specialist_traces_and_snapshot(self):
        original = Records.trace
        calls = []
        def fail(rows, event):
            if event['actor'] == 'exception':
                calls.append(event)
                if len(calls) == 2:
                    raise OSError('Synthetic import failure')
            return original(rows, event)
        view = self.case()
        with patch.object(Records, 'trace', fail):
            result = self.dispatch(view)
        self.assertEqual(result['case']['status'], 'HUMAN_ASSISTANCE')
        self.assertFalse(self.repo.list('exception_run'))
        self.assertFalse(any(e['actor'] == 'exception' for e in self.repo.find_by_case(view['case']['caseId'])))

    def test_confirmed_clarification_resumes_same_case_and_preserves_attempts(self):
        view = self.dispatch(self.case('missing-evidence'))
        self.assertEqual(view['case']['status'], 'AWAITING_REQUESTER')
        case_id = view['case']['caseId']
        intents = [{'caseType': 'DISRUPTION', 'fields': view['fields']}]
        with self.assertRaises(OperationsError):
            self.service.clarify(PAID, self.key(), case_id, view['revision'], intents, False)
        old = self.contexts.contexts[case_id]
        _, repaired = fixture()
        repaired.update(caseId=case_id, travellerId=PAID)
        repaired['itinerary']['travellerId'] = PAID
        self.contexts.contexts[case_id] = repaired
        view = self.service.clarify(PAID, self.key(), case_id, view['revision'], intents, True)
        view = self.dispatch(view)
        self.assertEqual(view['case']['status'], 'UNDER_REVIEW')
        self.assertEqual(len(self.exceptions.recent()), 2)
        self.assertTrue(any(s['context']['evidence'] == old['evidence'] for s in self.exceptions.recent()))

    def test_revised_proposal_has_lineage_and_old_decision_cannot_authorise_it(self):
        view = self.dispatch(self.case('approval'))
        case_id = view['case']['caseId']
        first = self.bridge.investigation(OPERATOR, case_id)
        view = self.review(view, 'REQUEST_REVISION')
        view = self.service.clarify(PAID, self.key(), case_id, view['revision'],
                                    [{'caseType':'DISRUPTION','fields':view['fields']}], True)
        view = self.dispatch(view)
        second = self.bridge.investigation(OPERATOR, case_id)
        self.assertEqual(second['proposal']['previousSubject'], first['proposal']['subject'])
        self.assertEqual(second['proposal']['subject']['materialVersion'], 2)
        self.assertEqual(view['case']['status'], 'AWAITING_HUMAN_APPROVAL')
        with self.assertRaises(OperationsError):
            self.service.deliver(OPERATOR, self.key(), case_id, view['revision'])

    def test_shared_reviewer_recalculates_cost_and_fails_unknown_domains(self):
        view = self.dispatch(self.case())
        snapshot = self.bridge.investigation(OPERATOR, view['case']['caseId'])
        proposal = deepcopy(snapshot['proposal'])
        self.assertEqual(snapshot['result']['review']['policyVersion'], 'shared-deterministic-review-1')
        proposal['options'][0]['totalCost'] = '1.00'
        review = self.bridge.runtime.reviewer.review(proposal, snapshot['result']['sourceReferences'], [])
        self.assertEqual(review['outcome'], 'REVISION_REQUIRED')
        from tripmate.services.review import DeterministicReviewService
        review = DeterministicReviewService(lambda: TIME, {}).review(
            snapshot['proposal'], snapshot['result']['sourceReferences'], [])
        self.assertEqual(review['outcome'], 'REVISION_REQUIRED')

    def test_failed_review_can_be_corrected_without_reusing_previous_review(self):
        view = self.case('review-failed')
        case_id = view['case']['caseId']
        reviewer = self.bridge.runtime.reviewer
        original = reviewer.review

        def failed(*args):
            review = original(*args)
            review.update(outcome='REVISION_REQUIRED', reasons=['Controlled review failure for revision evidence.'])
            return review

        with patch.object(reviewer, 'review', side_effect=failed):
            view = self.dispatch(view)
        self.assertEqual(view['case']['status'], 'AWAITING_REQUESTER')
        first = self.bridge.investigation(OPERATOR, case_id)
        view = self.service.clarify(PAID, self.key(), case_id, view['revision'],
                                    [{'caseType': 'DISRUPTION', 'fields': view['fields']}], True)
        view = self.dispatch(view)
        second = self.bridge.investigation(OPERATOR, case_id)
        self.assertEqual(view['case']['status'], 'UNDER_REVIEW')
        self.assertEqual(second['proposal']['previousReviewId'], first['result']['review']['reviewId'])
        self.assertEqual(second['proposal']['subject']['materialVersion'], 2)
        self.assertNotEqual(second['result']['review']['reviewId'], first['result']['review']['reviewId'])

    def test_late_exception_result_cannot_overwrite_withdrawal(self):
        import threading
        view = self.case()
        case_id = view['case']['caseId']
        ready, release = threading.Event(), threading.Event()
        original = self.bridge.handle_case
        results = []

        def delayed(case):
            result = original(case)
            ready.set()
            if not release.wait(5):
                raise TimeoutError('Controlled late result')
            return result

        with patch.object(self.bridge, 'handle_case', side_effect=delayed):
            thread = threading.Thread(target=lambda: results.append(self.dispatch(view)))
            thread.start()
            try:
                self.assertTrue(ready.wait(5))
                current = self.service.case_view(PAID, case_id)
                self.service.case_action(PAID, self.key(), case_id, current['revision'], 'WITHDRAW', 'Synthetic withdrawal')
            finally:
                release.set()
                thread.join(timeout=5)
        self.assertFalse(thread.is_alive())
        self.assertEqual(results[0]['case']['status'], 'WITHDRAWN')
        self.assertEqual(len(self.exceptions.recent()), 1)
        self.assertEqual(self.repo.list('exception_run'), [])


if __name__ == '__main__':
    unittest.main()
