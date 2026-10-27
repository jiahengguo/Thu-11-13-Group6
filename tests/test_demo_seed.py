"""Explicit demo identity provisioning and domain-service seed data, without cloud writes."""
import json
from pathlib import Path
import tempfile
import unittest
from uuid import UUID

from test_portals import FakeCloud
from tripmate.portal.demo import prepare_accounts, seed_data, supplier_inputs
from tripmate.portal.server import Portal
from tripmate.fixtures.b03 import FIXTURE_TIME
from tripmate.supplier.common import PricingPolicy


class DemoCloud(FakeCloud):
    url = 'https://demo.supabase.co'
    def __init__(self):
        super().__init__()
        self.demo_users = {}
        self.created = 0
    def request(self, path, method='GET', body=None, token=None, admin=False):
        if path == '/auth/v1/admin/users' and method == 'POST':
            assert admin
            actor, _ = self.add()
            self.created += 1
            user = dict(id=actor, email=body['email'], app_metadata=body['app_metadata'])
            self.demo_users[actor] = user
            return user
        if path.startswith('/auth/v1/admin/users/'):
            assert admin
            return self.demo_users[path.rsplit('/', 1)[1]]
        return super().request(path, method, body, token, admin)
    def rpc(self, name, body=None):
        if name == 'tripmate_prepare_demo_profile':
            actor = body['actor']
            if actor:
                user = self.demo_users[actor]
                assert user['app_metadata']['tripmate_demo'] == body['demo_namespace']
                kind = body['member_kind']
                self.accounts[actor].update(role={'supplier': 'SUPPLIER', 'operator': 'OPERATOR'}.get(kind, 'TRAVELLER'),
                    membership='PAID' if kind == 'paid' else 'FREE', paidUntil='2026-11-26T00:00:00+11:00' if kind == 'paid' else None)
            return {'demoProvisioning': 1}
        return super().rpc(name, body)


class DemoSeedTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / '.demo-accounts.local.json'
        self.cloud = DemoCloud()
        self.manifest = prepare_accounts(self.cloud, 'stage2-test', self.path)

    def test_provisioning_resumes_without_rotating_existing_passwords(self):
        before = json.loads(self.path.read_text())
        again = prepare_accounts(self.cloud, 'stage2-test', self.path)
        self.assertEqual(self.cloud.created, 4)
        self.assertEqual(again, before)
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(len({a['password'] for a in again['accounts'].values()}), 4)
        for account in again['accounts'].values():
            UUID(account['id'])

    def test_other_project_namespace_and_tampered_identity_are_rejected(self):
        with self.assertRaises(ValueError):
            prepare_accounts(self.cloud, 'another-test', self.path)
        actor = self.manifest['accounts']['operator']['id']
        self.cloud.demo_users[actor]['app_metadata']['tripmate_demo'] = 'different-test'
        with self.assertRaises(ValueError):
            prepare_accounts(self.cloud, 'stage2-test', self.path)

    def test_seed_requires_real_role_evidence_and_does_not_assign_it(self):
        self.cloud.accounts[self.manifest['accounts']['supplier']['id']]['role'] = 'TRAVELLER'
        with self.assertRaises(ValueError):
            seed_data(self.cloud, self.manifest['accounts'], 'stage2-test', clock=lambda: FIXTURE_TIME)
        self.assertEqual(self.cloud.state['records'], [])

    def test_seed_is_repeatable_preserves_unrelated_data_and_requires_review(self):
        from tripmate.portal.repository import SupabaseOperationsRepository
        with SupabaseOperationsRepository(self.cloud).transaction() as rows:
            rows.put('unrelated', 'keep', {'saved': True})
        first = seed_data(self.cloud, self.manifest['accounts'], 'stage2-test', start_date='2026-10-20', clock=lambda: FIXTURE_TIME)
        before = json.loads(json.dumps(self.cloud.state))
        again = seed_data(self.cloud, self.manifest['accounts'], 'stage2-test', clock=lambda: FIXTURE_TIME)
        self.assertEqual(first, again)
        self.assertEqual(self.cloud.state, before)
        self.assertEqual(len(first['supplierCases']), 7)
        app = Portal(self.cloud)
        app.operations.clock = lambda: FIXTURE_TIME
        app.operations.entitlement.clock = lambda: FIXTURE_TIME
        app.supplier.runtime.clock = lambda: FIXTURE_TIME
        app.supplier.pricing.clock = lambda: FIXTURE_TIME
        operator = self.manifest['accounts']['operator']['id']
        for name in ('express', 'coach', 'stay', 'activity'):
            cid = first['supplierCases'][name]
            assessment = app.supplier.view(operator, cid)
            self.assertEqual(assessment['status'], 'UNDER_REVIEW')
            self.assertEqual(assessment['price']['sellingPrice']['amount'], '198.00')
        for name, expected in (('expired', 'EXPIRED'), ('zero-stock', 'REVISION_REQUIRED')):
            self.assertEqual(app.supplier.view(operator, first['supplierCases'][name])['status'], expected)
        self.assertEqual(app.supplier.find_selectable({}, FIXTURE_TIME), [])
        for kind, intake_id in first['travellerDrafts'].items():
            draft = app.operations.repository.read('intake', intake_id)
            self.assertEqual(draft['caseIds'], [])
            self.assertEqual(draft['state'], 'AWAITING_CONFIRMATION')
        self.assertEqual(app.operations.repository.read('unrelated', 'keep'), {'saved': True})

    def test_seed_date_changes_require_a_new_scenario(self):
        seed_data(self.cloud, self.manifest['accounts'], 'stage2-test', start_date='2026-10-20', clock=lambda: FIXTURE_TIME)
        with self.assertRaises(ValueError):
            seed_data(self.cloud, self.manifest['accounts'], 'stage2-test', start_date='2026-10-21', clock=lambda: FIXTURE_TIME)
        with self.assertRaises(ValueError):
            seed_data(self.cloud, self.manifest['accounts'], 'stage2-test', clock=lambda: '2026-11-05T00:00:00+11:00')

    def test_reviewed_seed_inventory_generates_a_complete_plan(self):
        seed = seed_data(self.cloud, self.manifest['accounts'], 'stage2-test', start_date='2026-10-20', clock=lambda: FIXTURE_TIME)
        app = Portal(self.cloud, supplier_policy=PricingPolicy('0.10', '15.00', 'demo-2026-10-24'))
        app.operations.clock = app.operations.entitlement.clock = lambda: FIXTURE_TIME
        app.supplier.runtime.clock = app.supplier.pricing.clock = lambda: FIXTURE_TIME
        operator = self.manifest['accounts']['operator']['id']
        for name in ('express', 'coach', 'stay', 'activity', 'restricted'):
            cid = seed['supplierCases'][name]
            rec = app.operations.repository.read('case', cid)
            view = app.supplier.view(operator, cid)
            reviewed = app.supplier.mutate(operator, 'review', dict(caseId=cid, revision=rec['revision'],
                materialVersion=view['offer']['materialVersion'], decision='PASS',
                reason='Test operator explicitly verified synthetic source and configured price.', requestKey='review-' + name))
            self.assertEqual(reviewed['status'], 'AWAITING_APPROVAL' if name == 'restricted' else 'APPROVED')
        paid = self.manifest['accounts']['paid']['id']
        draft = app.operations.repository.read('intake', seed['travellerDrafts']['paid'])
        confirmed = app.operations.confirm(paid, 'confirm-demo', draft['id'], draft['revision'], draft['intents'], True)
        result = app.operations.dispatch(paid, 'generate-demo', confirmed['caseIds'][0], 1)
        self.assertEqual(result['case']['status'], 'UNDER_REVIEW', result)
        rec = app.operations.repository.read('case', confirmed['caseIds'][0])
        versions = [app.planning.get_version(s['subjectId'])['version'] for s in rec['specialistResult']['subjects']]
        self.assertTrue(versions)
        for version in versions:
            self.assertEqual(version['totalPrice']['amount'], '594.00')
