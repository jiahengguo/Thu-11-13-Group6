"""UC-03/04 positive and failure-path evidence against executed prototype rules."""
import json
import sqlite3
import tempfile
import threading
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
from urllib import request, error
from tripmate.agents.exception import CustomerExceptionAgent
from tripmate.exception_handling.fixtures import fixture, demo_runtime
from tripmate.exception_handling.ports import MemoryContext, SimulatedSupplier, SimulatedPlanning, SimulatedReviewer
from tripmate.exception_handling import ExceptionRuntime, ExceptionRepository
from tripmate.contracts import validate, ContractError
from tripmate.api.server import make_server
from tripmate.api.settings import Settings

class ExceptionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'tripmate.sqlite3'
        self.repo = ExceptionRepository(self.path)

    def run_case(self, kind='DISRUPTION', scenario='normal', edit=None, planning=None, reviewer=None):
        case, ctx = fixture(kind, scenario)
        if edit:
            edit(case, ctx)
        runtime = ExceptionRuntime(MemoryContext({case['caseId']: ctx}), self.repo,
                                   SimulatedSupplier(), planning or SimulatedPlanning(), reviewer or SimulatedReviewer())
        original = deepcopy((case, ctx))
        result = CustomerExceptionAgent(runtime).handle_case(case)
        self.assertEqual((case, ctx), original, 'Input case and baseline must never be mutated')
        validate('AgentResult', result)
        return result, self.repo.get(result['runId'])

    def test_disruption_cost_timing_rejections_and_persistent_trace(self):
        r, saved = self.run_case()
        self.assertEqual(r['status'], 'SUCCESS')
        self.assertEqual(saved['proposal']['options'][0]['totalCost'], '680.00')
        self.assertEqual(saved['proposal']['options'][0]['arrivalChangeMinutes'], 60)
        self.assertEqual(saved['proposal']['rejectedOptions'][0]['offerId'], 'replacement-late')
        self.assertEqual(saved['context']['itinerary']['items'][0]['itemId'], 'flight-original')
        self.assertEqual(saved['handoffTo'], 'operations')
        self.assertTrue(saved['caseRemainsOpen'])
        self.assertEqual(r['review']['subject'], r['subjects'][0])
        self.assertTrue(all(c['outcome'] == 'PASS' for c in r['validationResults']))
        ids = {s['sourceId'] for s in r['sourceReferences']}
        self.assertTrue(all(set(c['sourceIds']) <= ids for c in r['validationResults']))
        for e in saved['trace']:
            validate('TraceEvent', e)
        self.assertTrue({'INTAKE','TOOL_RESULT','VALIDATION','VERSION_CREATED','REVIEW','HANDOFF'} <= {e['eventType'] for e in saved['trace']})
        self.assertEqual(ExceptionRepository(self.path).get(r['runId']), saved)
        self.assertEqual(self.repo.find_by_case(r['caseId']), saved['trace'])

    def test_complaint_has_service_evidence_policy_and_no_financial_entitlement(self):
        r, saved = self.run_case('COMPLAINT')
        self.assertEqual(r['status'], 'SUCCESS')
        self.assertEqual(saved['proposal']['delayMinutes'], 90)
        self.assertEqual(saved['proposal']['policyIds'], ['delay-demo'])
        self.assertFalse(r['requiresApproval'])
        self.assertEqual(saved['approvals'], [])
        self.assertIn('No refund or compensation entitlement', r['proposedResponse'])

    def test_uncertainty_and_unsafe_cases_go_to_operations_with_recorded_reasons(self):
        for kind in ('DISRUPTION','COMPLAINT'):
            for scenario in ('conflict','missing-evidence','no-alternative','low-confidence','safety'):
                with self.subTest(kind=kind, scenario=scenario):
                    r, saved = self.run_case(kind, scenario)
                    self.assertEqual(r['status'], 'HUMAN_ASSISTANCE')
                    self.assertIsNone(r['proposedResponse'])
                    self.assertTrue(saved['referral']['humanHandlingRequired'])
                    self.assertTrue(saved['referral']['reason'])
                    self.assertEqual(saved['referral']['to'], 'operations')

    def test_approval_is_pending_saved_and_version_scoped_never_a_human_decision(self):
        for kind in ('DISRUPTION','COMPLAINT'):
            r, saved = self.run_case(kind, 'approval')
            self.assertEqual(r['status'], 'APPROVAL_PENDING')
            self.assertTrue(r['requiresApproval'])
            approval = saved['approvals'][0]
            validate('Approval', approval)
            self.assertEqual(approval['subject'], r['subjects'][0])
            self.assertEqual(approval['reviewId'], r['review']['reviewId'])
            self.assertEqual(approval['approvalId'], r['approvalIds'][0])
            self.assertIsNone(approval['decision'])
            self.assertIsNone(approval['operatorId'])

    def test_unconfirmed_closed_withdrawn_wrong_owner_or_type_blocked(self):
        edits = [lambda c,x: c.update(status='WITHDRAWN'), lambda c,x: c.update(status='CLOSED'),
                 lambda c,x: c.update(primaryHandler='supplier'), lambda c,x: c.update(caseType='ROUTINE_ENQUIRY'),
                 lambda c,x: x.update(travellerId='someone-else'), lambda c,x: c.update(humanRequestCount=2),
                 lambda c,x: c.update(unresolvedQuestions=['Unconfirmed details'])]
        for edit in edits:
            with self.subTest(edit=edit):
                r, _ = self.run_case(edit=edit)
                self.assertEqual(r['status'], 'HUMAN_ASSISTANCE')

    def test_expired_future_unknown_or_ambiguous_sources_block(self):
        edits = [lambda c,x: x['evidence'][0].update(validUntil='2026-10-20T07:00:00+11:00'),
                 lambda c,x: x['evidence'][0]['source'].update(freshness='UNKNOWN'),
                 lambda c,x: x['evidence'][0]['source'].update(capturedAt='2026-10-21T07:00:00+11:00'),
                 lambda c,x: x['evidence'].append(deepcopy(x['evidence'][0])),
                 lambda c,x: x['itinerary']['items'][0].update(sourceIds=['missing'])]
        for edit in edits:
            r, _ = self.run_case(edit=edit)
            self.assertEqual(r['status'], 'HUMAN_ASSISTANCE')

    def test_budget_availability_route_and_downstream_time_checks_are_executed(self):
        edits = [lambda c,x: x['constraints'][0].update(value='600.00'),
                 lambda c,x: [o.update(available=False) for o in x['supplierOffers']],
                 lambda c,x: [o.update(validUntil='2026-10-20T07:00:00+11:00') for o in x['supplierOffers']],
                 lambda c,x: [o['replacement'].update(destination='BNE') for o in x['supplierOffers']],
                 lambda c,x: x['itinerary']['items'][1].update(startAt='2026-10-20T11:00:00+11:00')]
        for edit in edits:
            r, _ = self.run_case(edit=edit)
            self.assertEqual(r['status'], 'HUMAN_ASSISTANCE')
            self.assertEqual(r['errors'][0]['code'], 'NO_FEASIBLE_ITINERARY')

    def test_policy_requires_actual_source_and_supported_action(self):
        edits = [lambda c,x: x['policies'][0].update(sourceIds=['operations-confirmation']),
                 lambda c,x: x['policies'][0].update(action='HUMAN_REVIEW_REFUND')]
        for edit in edits:
            r, _ = self.run_case('COMPLAINT', edit=edit)
            self.assertEqual(r['status'], 'HUMAN_ASSISTANCE')
            self.assertTrue(any(c['ruleId'] == 'EXC_POLICY_EVIDENCE' and c['outcome'] == 'FAIL'
                                for c in r['validationResults']))

    def test_explicit_transfer_allowance_and_schedule_discrepancy(self):
        r, _ = self.run_case(edit=lambda c,x: x['itinerary']['items'][1].update(startAt='2026-10-20T12:00:00+11:00'))
        self.assertEqual(r['errors'][0]['code'], 'NO_FEASIBLE_ITINERARY')
        r, _ = self.run_case('COMPLAINT', edit=lambda c,x: x['itinerary']['items'][0].update(endAt='2026-10-20T11:00:00+11:00'))
        self.assertEqual(r['status'], 'HUMAN_ASSISTANCE')
        self.assertTrue(any(c['ruleId'] == 'EXC_SCHEDULE_MATCH' and c['outcome'] == 'FAIL'
                            for c in r['validationResults']))

    def test_unknown_constraint_cannot_be_silently_ignored(self):
        r, _ = self.run_case(edit=lambda c,x: x['constraints'].append({'name':'wheelchair','value':'required'}))
        self.assertEqual(r['errors'][0]['code'], 'UNSUPPORTED_CONSTRAINT')

    def test_planner_cannot_drop_hotel_or_mutate_baseline(self):
        class BadPlanning:
            def revise(self, context, offer):
                return [offer['replacement']]
        r, _ = self.run_case(planning=BadPlanning())
        self.assertEqual(r['status'], 'HUMAN_ASSISTANCE')

    def test_dependency_and_review_failures_do_not_claim_reviewed_success(self):
        for scenario in ('dependency-unavailable', 'review-failed'):
            case, runtime = demo_runtime(self.repo, 'DISRUPTION', scenario)
            r = CustomerExceptionAgent(runtime).handle_case(case)
            self.assertEqual(r['status'], 'HUMAN_ASSISTANCE')
            self.assertIsNone(r['proposedResponse'])
            self.assertIsNotNone(self.repo.get(r['runId']))

    def test_wrong_version_review_rejected(self):
        class BadReviewer(SimulatedReviewer):
            def review(self, subject, evidence, policies):
                r = super().review(subject, evidence, policies)
                r['subject']['materialVersion'] = 99
                return r
        r, _ = self.run_case(reviewer=BadReviewer())
        self.assertEqual(r['status'], 'HUMAN_ASSISTANCE')
        self.assertEqual(r['errors'][0]['code'], 'REVIEW_FAILED')

    def test_save_failure_has_no_success_approval_or_durable_handoff(self):
        with patch.object(self.repo, 'save', side_effect=sqlite3.OperationalError('disk full')):
            r, saved = self.run_case('COMPLAINT','approval')
        self.assertEqual(r['status'], 'FAILURE')
        self.assertEqual(r['errors'][0]['code'], 'PERSISTENCE_FAILED')
        self.assertIsNone(saved)
        self.assertIsNone(r['review'])
        self.assertEqual(r['approvalIds'], [])

    def test_reruns_append_and_never_reuse_prior_approval(self):
        one, _ = self.run_case('COMPLAINT','approval')
        two, _ = self.run_case('COMPLAINT','approval')
        self.assertNotEqual(one['subjects'], two['subjects'])
        self.assertNotEqual(one['approvalIds'], two['approvalIds'])
        self.assertEqual(len(self.repo.recent()), 2)

    def test_missing_context_fields_and_real_sources_fail_closed(self):
        for edit in (lambda c,x: x.pop('evidence'), lambda c,x: x['evidence'][0]['source'].update(simulated=False)):
            r, _ = self.run_case(edit=edit)
            self.assertEqual(r['status'], 'HUMAN_ASSISTANCE')


class ExceptionWebTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.server = make_server(Settings(Path(self.tmp.name)/'web.sqlite3'), 0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop)
        self.url = 'http://127.0.0.1:' + str(self.server.server_port)
        self.token = self.get('/api/status')['csrfToken']

    def stop(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(2)

    def get(self, path):
        with request.urlopen(self.url + path) as r:
            return json.load(r)

    def post(self, data, token=None, path='/api/exception-demo'):
        req = request.Request(self.url + path, json.dumps(data).encode(), headers={
            'Content-Type':'application/json', 'X-TripMate-Token':token or self.token})
        with request.urlopen(req) as r:
            return json.load(r)

    def test_two_web_demos_history_and_reset_retention(self):
        with request.urlopen(self.url) as r:
            html = r.read().decode()
        self.assertIn('exception-disruption', html)
        self.assertIn('exception-complaint', html)
        for kind in ('DISRUPTION','COMPLAINT'):
            data = self.post({'kind':kind})
            self.assertEqual(data['result']['status'], 'SUCCESS')
        self.post({}, path='/api/fixtures/reset')
        self.assertEqual(len(self.get('/api/exception-runs')['runs']), 2)

    def test_token_unknown_fields_and_stub_mode_are_rejected(self):
        with self.assertRaises(error.HTTPError) as cm:
            self.post({'kind':'DISRUPTION'}, 'bad-token')
        self.assertEqual(cm.exception.code, 403)
        with self.assertRaises(error.HTTPError) as cm:
            self.post({'kind':'DISRUPTION', 'executeRefund': True})
        self.assertEqual(cm.exception.code, 400)
        self.server.app.exception_repository = None
        with self.assertRaises(error.HTTPError) as cm:
            self.post({'kind':'COMPLAINT'})
        self.assertEqual(cm.exception.code, 422)

if __name__ == '__main__':
    unittest.main()
