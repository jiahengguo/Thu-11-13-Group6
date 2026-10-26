"""Model proposal routing through actual portal services; transport is explicitly a test double."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from test_demo_seed import DemoCloud
from tripmate.portal.demo import prepare_accounts, seed_data
from tripmate.portal.server import Portal
from tripmate.fixtures.b03 import FIXTURE_TIME
from tripmate.supplier.common import PricingPolicy
from tripmate.planning.common import PlanningError


class ProposalClient:
    model = 'TEST_DOUBLE_NOT_REAL_MODEL'
    def __init__(self, mode):
        self.mode, self.calls, self.messages = mode, 0, []
    def chat(self, messages):
        self.calls += 1
        self.messages.append(messages)
        if self.mode == 'unavailable':
            raise PlanningError('TOOL_UNAVAILABLE', 'Test transport failure', 'llm')
        inventory = json.loads(messages[1]['content'])['inventory']
        ids = [next(q['offerId'] for q in inventory if q['product']['role'] == role)
               for role in ('OUTBOUND', 'STAY', 'ACTIVITY')]
        return json.dumps(dict(candidates=[ids if self.mode == 'valid' else ['invented-offer']], explanation='Test draft'))


class ModelPlanningPortalTests(unittest.TestCase):
    def setUp(self):
        self.cloud = DemoCloud()
        with tempfile.TemporaryDirectory() as folder:
            self.accounts = prepare_accounts(self.cloud, 'model-test', Path(folder) / '.demo-accounts.local.json')['accounts']
        self.seed = seed_data(self.cloud, self.accounts, 'model-test', start_date='2026-10-20', clock=lambda: FIXTURE_TIME)

    def prepare(self, mode):
        client = ProposalClient(mode)
        with patch.dict('os.environ', {'ELEC5620_API_KEY': 'test-only', 'TRIPMATE_LLM_PROVIDER': 'elec5620'}, clear=True), \
             patch('tripmate.adapters.campus.CampusClient', return_value=client) as factory:
            app = Portal(self.cloud, supplier_policy=PricingPolicy('0.10', '15.00', 'demo-2026-10-24'), model_planning=True)
            app.operations.clock = app.operations.entitlement.clock = lambda: FIXTURE_TIME
            app.supplier.runtime.clock = app.supplier.pricing.clock = lambda: FIXTURE_TIME
            operator = self.accounts['operator']['id']
            for name in ('express', 'coach', 'stay', 'activity'):
                cid = self.seed['supplierCases'][name]
                rec = app.operations.repository.read('case', cid)
                view = app.supplier.view(operator, cid)
                app.supplier.mutate(operator, 'review', dict(caseId=cid, revision=rec['revision'],
                    materialVersion=view['offer']['materialVersion'], decision='PASS', reason='Test operator verified offer.',
                    requestKey='review-' + name))
            paid = self.accounts['paid']['id']
            draft = app.operations.repository.read('intake', self.seed['travellerDrafts']['paid'])
            confirmed = app.operations.confirm(paid, 'confirm', draft['id'], draft['revision'], draft['intents'], True)
            cid = confirmed['caseIds'][0]
            result = app.operations.dispatch(paid, 'dispatch', cid, 1)
            factory.assert_called_with(timeout=20, max_completion_tokens=1024)
            return app, result, app.operations.repository.read('case', cid), client

    def test_model_proposal_is_validated_and_saved_without_identity_in_prompt(self):
        app, result, rec, client = self.prepare('valid')
        self.assertEqual(result['case']['status'], 'UNDER_REVIEW', result)
        self.assertEqual(client.calls, 1)
        version = app.planning.get_version(rec['specialistResult']['subjects'][0]['subjectId'])
        self.assertEqual(version['modelPlanning']['model'], 'TEST_DOUBLE_NOT_REAL_MODEL')
        self.assertEqual(version['version']['totalPrice']['amount'], '594.00')
        self.assertTrue(all(v['outcome'] == 'PASS' for v in version['version']['validationResults']))
        prompt = json.dumps(client.messages)
        for identity in self.accounts.values():
            self.assertNotIn(identity['email'], prompt)
            self.assertNotIn(identity['id'], prompt)
            self.assertNotIn(identity['password'], prompt)
        self.assertNotIn('supplierCost', prompt)

    def test_model_unavailable_has_no_deterministic_success_fallback(self):
        app, result, rec, client = self.prepare('unavailable')
        self.assertNotEqual(result['case']['status'], 'UNDER_REVIEW')
        self.assertEqual(client.calls, 1)
        self.assertEqual(rec['specialistResult']['subjects'], [])
        self.assertEqual(rec['specialistResult']['errors'][0]['code'], 'TOOL_UNAVAILABLE')

    def test_invalid_model_offers_are_rejected_after_bounded_repairs(self):
        _, result, rec, client = self.prepare('invalid')
        self.assertNotEqual(result['case']['status'], 'UNDER_REVIEW')
        self.assertEqual(client.calls, 3)
        self.assertEqual(rec['specialistResult']['subjects'], [])

    def test_model_mode_rejects_missing_configuration_at_startup(self):
        with patch.dict('os.environ', {}, clear=True):
            with self.assertRaises(PlanningError):
                Portal(self.cloud, model_planning=True)
