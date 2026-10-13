"""Optional real B04/Planning integration, skipped when Moore's branch is absent."""
import tempfile
import unittest
from importlib.util import find_spec
from pathlib import Path

from tripmate.supplier.fixtures import fixture_runtime


@unittest.skipUnless(find_spec('tripmate.planning'), 'Merge B04/Planning before running integration checks')
class SupplierPlanningIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.database = Path(self.tmp.name) / 'supplier.sqlite3'

    def test_b03_positive_and_negative_scenarios_use_actual_b04(self):
        expected = {'coach': 'SUCCESS', 'express': 'SUCCESS', 'basic-stay': 'SUCCESS',
                    'comfort-stay': 'SUCCESS', 'walk': 'SUCCESS', 'guided-tour': 'SUCCESS',
                    'expired': 'FAILURE', 'zero-stock': 'FAILURE', 'missing-cost': 'FAILURE',
                    'unsupported-currency': 'FAILURE', 'missing-terms': 'FAILURE',
                    'pending-approval': 'APPROVAL_PENDING'}
        for scenario, status in expected.items():
            with self.subTest(scenario=scenario):
                case, runtime = fixture_runtime(self.database, scenario)
                result = runtime.handle_case(case)
                self.assertEqual(result['status'], status, result)
        self.assertEqual(len(runtime.find_selectable({}, runtime.clock())), 6)

    def test_planning_consumes_b08_lookup_without_changing_moore_code(self):
        from tripmate.planning.fixtures import fixture_runtime as planning_fixture
        from tripmate.agents.planning import TravelPlanningAgent
        for scenario in ('coach', 'express', 'basic-stay', 'comfort-stay', 'walk', 'guided-tour'):
            case, supplier = fixture_runtime(self.database, scenario)
            self.assertEqual(supplier.handle_case(case)['status'], 'SUCCESS')
        case, _, planning = planning_fixture(database=str(Path(self.tmp.name) / 'planning.sqlite3'))
        planning.offers = supplier
        try:
            result = TravelPlanningAgent(planning).handle_case(case)
            self.assertEqual(result['status'], 'SUCCESS', result)
            self.assertTrue(result['subjects'])
        finally:
            planning.repository.close()

    def test_human_approval_is_explicit_and_price_policy_revision_blocks_selection(self):
        from copy import deepcopy
        from tripmate.supplier import PricingPolicy
        case, runtime = fixture_runtime(self.database, 'pending-approval')
        self.assertEqual(runtime.handle_case(case)['status'], 'APPROVAL_PENDING')
        offer = runtime.repository.current('candidate-pending-approval')['offer']
        approval = runtime.approvals.find_by_subject({'subjectType': 'SupplierOffer',
                        'subjectId': offer['offerId'], 'materialVersion': offer['materialVersion']})[-1]
        decision = deepcopy(approval)
        decision.update(status='DECIDED', decision='APPROVE', operatorId='fixture-human',
                        decidedAt=runtime.clock(), reason='Explicit synthetic test human decision')
        runtime.approvals.save(decision)
        self.assertEqual(runtime.apply_decision(decision)['status'], 'SUCCESS')
        self.assertEqual(len(runtime.find_selectable({}, runtime.clock())), 1)
        runtime.policy = PricingPolicy('0.20', '0.00', 'revised-policy')
        self.assertEqual(runtime.find_selectable({}, runtime.clock()), [])

    def test_web_supplier_assessment_and_repeat_reset_are_isolated(self):
        import json
        import threading
        from contextlib import closing
        from urllib.request import Request, urlopen
        from tripmate.api.server import make_server
        from tripmate.api.settings import Settings
        from tripmate.supplier import SupplierRepository
        shared = Path(self.tmp.name) / 'shared.sqlite3'
        server = make_server(Settings(shared), port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f'http://127.0.0.1:{server.server_port}'
        try:
            with urlopen(base + '/api/status', timeout=5) as response:
                token = json.load(response)['csrfToken']
            def post(path, payload):
                req = Request(base + path, data=json.dumps(payload).encode(), method='POST',
                              headers={'Content-Type': 'application/json', 'X-TripMate-Token': token})
                with urlopen(req, timeout=5) as response:
                    return json.load(response)
            first = post('/api/supplier-demo', {'scenario': 'coach'})
            self.assertEqual(first['result']['status'], 'SUCCESS')
            self.assertEqual(first['evidence']['details']['modelExecution'], 'FIXTURE_REPLAY')
            self.assertEqual(post('/api/supplier-demo', {'scenario': 'zero-stock'})['result']['status'], 'FAILURE')
            self.assertEqual(post('/api/supplier-demo', {'scenario': 'pending-approval'})['result']['status'], 'APPROVAL_PENDING')
            second = post('/api/supplier-demo', {'scenario': 'coach'})
            self.assertEqual(second['snapshot']['offer']['materialVersion'], 2)
            self.assertNotEqual(server.app.supplier_db, shared)
            real_records = SupplierRepository(shared)
            real_records.reserve('unrelated-team-offer', 'team-case', 'REAL')
            post('/api/fixtures/reset', {})
            post('/api/fixtures/reset', {})
            self.assertEqual(SupplierRepository(server.app.supplier_db).records(), [])
            self.assertIsNotNone(real_records.current('unrelated-team-offer'))
            reset_offer = post('/api/supplier-demo', {'scenario': 'coach'})
            self.assertEqual(reset_offer['snapshot']['offer']['materialVersion'], 1)
            with closing(__import__('sqlite3').connect(server.app.supplier_db)) as db:
                self.assertEqual(db.execute('SELECT COUNT(*) FROM supplier_fixture_approvals').fetchone()[0], 0)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == '__main__':
    unittest.main()
