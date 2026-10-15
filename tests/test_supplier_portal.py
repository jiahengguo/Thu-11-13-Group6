"""B02/B03/B08 portal adaptation using the existing protected cloud RPC protocol."""
import json
import threading
import unittest
from copy import deepcopy
from importlib.util import find_spec
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from test_portals import Browser, FakeCloud
from test_supplier import AT, TestPricing, example
from tripmate.portal.server import make_server
from tripmate.supplier import PricingPolicy
from tripmate.supplier.common import SOURCE_FIELDS


class SupplierPortalTests(unittest.TestCase):
    def setUp(self):
        self.cloud = FakeCloud()
        self.owner, _ = self.cloud.add('SUPPLIER')
        self.other, _ = self.cloud.add('SUPPLIER')
        self.operator, _ = self.cloud.add('OPERATOR')
        self.traveller, _ = self.cloud.add()
        self.server = make_server(self.cloud, port=0, supplier_pricing=TestPricing(),
                                  supplier_policy=PricingPolicy('0.10', '15.00', 'fixture-1'))
        self.server.app.operations.clock = lambda: AT
        self.server.app.supplier.runtime.clock = lambda: AT
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop)
        self.root = 'http://127.0.0.1:' + str(self.server.server_port)
        self.browser = Browser(self.root)
        self.browser.login(self.owner)

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def login(self, actor):
        self.browser = Browser(self.root)
        self.assertEqual(self.browser.login(actor)[0], 200)

    def operation(self, action, body):
        status, result, _ = self.browser.call('/api/operations/' + action, dict(requestKey=str(uuid4()), **body))
        self.assertEqual(status, 200, result)
        return result

    def submission(self):
        source = example('SupplierOffer.draft.json')
        payload = {key: deepcopy(source[key]) for key in SOURCE_FIELDS if key != 'supplierId'}
        payload.update(offerReference='quoted-service-1', sourceReference='synthetic://supplier/source-1')
        return payload

    def assess(self, payload=None):
        intents = [{'caseType': 'OFFER', 'fields': {'details': 'Confirmed synthetic quotation; no real commitment.',
                                                'supplierOffer': payload or self.submission()}}]
        intake = self.operation('intake', {'text': 'Assess the synthetic supplier quotation.', 'intents': intents})
        confirmed = self.operation('confirm', {'intakeId': intake['id'], 'revision': intake['revision'],
                                              'intents': intents, 'confirmed': True})
        case_id = confirmed['caseIds'][0]
        self.operation('dispatch', {'caseId': case_id, 'revision': 1})
        return case_id

    def view(self, case_id):
        status, data, _ = self.browser.call('/api/supplier/assessment?caseId=' + case_id)
        self.assertEqual(status, 200, data)
        return data

    def action(self, case_id, action='review', decision='PASS', key=None):
        assessment = self.view(case_id)
        status, case, _ = self.browser.call('/api/operations/case?caseId=' + case_id)
        self.assertEqual(status, 200)
        body = dict(caseId=case_id, materialVersion=assessment['offer']['materialVersion'],
                    revision=case['revision'], decision=decision, reason='Checked the synthetic source evidence and configured price.',
                    requestKey=key or str(uuid4()))
        return body, self.browser.call('/api/supplier/' + action, body)

    def test_authentication_ownership_privacy_and_explicit_review(self):
        case_id = self.assess()
        self.assertEqual(self.view(case_id)['status'], 'UNDER_REVIEW')
        self.assertIsNone(self.view(case_id)['price'])
        self.assertEqual(self.server.app.supplier.find_selectable({}, AT), [])
        self.login(self.other)
        self.assertEqual(self.browser.call('/api/supplier/assessment?caseId=' + case_id)[0], 403)
        self.login(self.traveller)
        self.assertEqual(self.browser.call('/api/supplier/assessment?caseId=' + case_id)[0], 403)
        self.login(self.operator)
        self.assertEqual(self.view(case_id)['price']['sellingPrice']['amount'], '198.00')
        body, result = self.action(case_id)
        self.assertEqual(result[0], 200, result)
        self.assertEqual(result[1]['status'], 'APPROVED')
        self.assertEqual(len(self.server.app.supplier.find_selectable({}, AT)), 1)
        self.assertEqual(self.browser.call('/api/supplier/review', body)[0], 200)
        self.login(self.owner)
        public = self.view(case_id)
        self.assertNotIn('pendingApprovals', public)
        self.assertIsNone(public['price'])
        self.assertNotIn('marginAmount', json.dumps(public))

    def test_restricted_terms_require_separate_version_scoped_decision(self):
        payload = self.submission()
        payload['commercialTerms'] = ['Restricted exclusive commitment']
        case_id = self.assess(payload)
        self.login(self.operator)
        _, reviewed = self.action(case_id)
        self.assertEqual(reviewed[1]['status'], 'AWAITING_APPROVAL')
        self.assertEqual(self.server.app.supplier.find_selectable({}, AT), [])
        status, case, _ = self.browser.call('/api/operations/case?caseId=' + case_id)
        self.assertEqual(case['case']['status'], 'AWAITING_HUMAN_APPROVAL')
        self.login(self.owner)
        fake = dict(caseId=case_id, materialVersion=1, revision=case['revision'], requestKey=str(uuid4()),
                    decision='APPROVE', reason='Supplier cannot self-approve.')
        self.assertEqual(self.browser.call('/api/supplier/decision', fake)[0], 403)
        self.login(self.operator)
        _, approved = self.action(case_id, 'decision', 'APPROVE')
        self.assertEqual(approved[1]['status'], 'APPROVED')
        self.assertEqual(len(self.server.app.supplier.find_selectable({}, AT)), 1)

    def test_source_revision_withdrawal_and_operator_revocation(self):
        first = self.assess()
        self.login(self.operator)
        self.action(first)
        self.login(self.owner)
        payload = self.submission()
        payload['availableQuantity'] = 0
        second = self.assess(payload)
        self.assertEqual(self.view(second)['status'], 'REVISION_REQUIRED')
        self.assertEqual(self.server.app.supplier.find_selectable({}, AT), [])
        self.assertEqual(self.view(first)['status'], 'NOT_ASSESSED')
        self.login(self.other)
        other_case = self.assess()
        self.assertEqual(self.view(other_case)['offer']['materialVersion'], 1)
        self.login(self.operator)
        self.cloud.accounts[self.operator]['role'] = 'TRAVELLER'
        self.assertEqual(self.browser.call('/api/supplier/assessment?caseId=' + other_case)[0], 403)

    def test_spoofed_identity_and_approval_fields_rejected_at_intake(self):
        for field, value in [('supplierId', self.other), ('status', 'APPROVED'), ('approvalId', 'fake'),
                             ('review', {}), ('markupRate', '0.99')]:
            payload = self.submission()
            payload[field] = value
            status, _, _ = self.browser.call('/api/operations/intake', {'requestKey': str(uuid4()), 'text': 'Synthetic offer',
                                     'intents': [{'caseType': 'OFFER', 'fields': {'details': 'Synthetic offer', 'supplierOffer': payload}}]})
            self.assertEqual(status, 422, field)

    def test_reconfirmation_atomically_withdraws_old_offer_and_reassesses_same_case(self):
        case_id = self.assess()
        self.login(self.operator)
        self.action(case_id)
        self.assertEqual(len(self.server.app.supplier.find_selectable({}, AT)), 1)
        self.login(self.owner)
        _, case, _ = self.browser.call('/api/operations/case?caseId=' + case_id)
        payload = self.submission()
        payload['commercialTerms'] = ['Material revised exclusive terms']
        self.operation('clarify', dict(caseId=case_id, revision=case['revision'], confirmed=True,
            intents=[{'caseType': 'OFFER', 'fields': {'details': 'Explicitly confirmed revised quotation', 'supplierOffer': payload}}]))
        self.assertEqual(self.server.app.supplier.find_selectable({}, AT), [])
        _, case, _ = self.browser.call('/api/operations/case?caseId=' + case_id)
        self.operation('dispatch', dict(caseId=case_id, revision=case['revision']))
        self.assertEqual(self.view(case_id)['offer']['materialVersion'], 2)
        self.assertEqual(self.view(case_id)['status'], 'UNDER_REVIEW')
        self.assertEqual(self.server.app.supplier.find_selectable({}, AT), [])

    def test_withdrawn_case_and_missing_pricing_cannot_leave_selectable_offers(self):
        case_id = self.assess()
        self.login(self.operator)
        self.action(case_id)
        self.login(self.owner)
        _, case, _ = self.browser.call('/api/operations/case?caseId=' + case_id)
        self.operation('case-action', dict(caseId=case_id, revision=case['revision'], action='WITHDRAW', reason='Withdraw synthetic source request'))
        self.assertEqual(self.server.app.supplier.find_selectable({}, AT), [])
        from tripmate.supplier.gateway import UnavailablePricing
        self.server.app.supplier.pricing = UnavailablePricing()
        self.server.app.supplier.runtime.pricing = self.server.app.supplier.pricing
        payload = self.submission()
        payload['offerReference'] = 'unconfigured-policy-offer'
        blocked = self.assess(payload)
        result = self.view(blocked)
        self.assertFalse(result['pricingReady'])
        self.assertEqual(result['issues'][0]['code'], 'TOOL_UNAVAILABLE')
        self.assertEqual(self.server.app.supplier.find_selectable({}, AT), [])

    def test_cloud_failure_after_domain_review_can_resume_same_action_without_duplicate(self):
        case_id = self.assess()
        self.login(self.operator)
        original = self.cloud.rpc
        def fail_case_commit(name, body=None):
            if name == 'tripmate_commit' and any(row['kind'] == 'case' for row in (body or {}).get('writes', [])):
                from tripmate.operations.common import OperationsError
                raise OperationsError('CLOUD_UNAVAILABLE', 'Injected case save failure')
            return original(name, body)
        with patch.object(self.cloud, 'rpc', side_effect=fail_case_commit):
            body, failed = self.action(case_id)
        self.assertEqual(failed[0], 503)
        self.assertEqual(self.view(case_id)['status'], 'APPROVED')
        revision = self.server.app.supplier.repository.current(self.view(case_id)['offer']['offerId'])['storageRevision']
        retry = self.browser.call('/api/supplier/review', body)
        self.assertEqual(retry[0], 200, retry)
        self.assertEqual(self.server.app.supplier.repository.current(self.view(case_id)['offer']['offerId'])['storageRevision'], revision)

    def test_cloud_fixture_reset_preserves_accounts_cases_offers_and_pending_decisions(self):
        case_id = self.assess()
        self.login(self.operator)
        accounts = deepcopy(self.cloud.accounts)
        self.assertEqual(self.browser.call('/api/demo/fixtures/reset', {})[0], 200)
        first = self.server.app.fixtures.snapshot()
        business = [deepcopy(row) for row in self.cloud.state['records'] if not row['kind'].startswith('demo_fixture')]
        self.assertEqual(self.browser.call('/api/demo/fixtures/reset', {})[0], 200)
        self.assertEqual(first, self.server.app.fixtures.snapshot())
        self.assertEqual(accounts, self.cloud.accounts)
        self.assertEqual(business, [row for row in self.cloud.state['records'] if not row['kind'].startswith('demo_fixture')])
        self.assertEqual(len(first['scenarios']), 11)
        self.assertEqual(self.view(case_id)['status'], 'UNDER_REVIEW')
        self.login(self.owner)
        self.assertEqual(self.browser.call('/api/demo/fixtures/reset', {})[0], 403)

    def test_failed_cloud_fixture_reset_rolls_back_and_rebuilds_pending_baseline(self):
        self.login(self.operator)
        self.browser.call('/api/demo/fixtures/reset', {})
        before = deepcopy(self.cloud.state)
        self.cloud.fail_commit = True
        self.assertEqual(self.browser.call('/api/demo/fixtures/reset', {})[0], 503)
        self.assertEqual(before, self.cloud.state)
        self.cloud.fail_commit = False
        with self.server.app.operations.repository.transaction() as rows:
            mutated = rows.get('demo_fixture_entity', 'approval:pending-exclusive')
            mutated['data']['status'] = 'APPROVED'
            rows.put('demo_fixture_entity', mutated['id'], mutated)
        self.browser.call('/api/demo/fixtures/reset', {})
        approval = next(row for row in self.server.app.fixtures.snapshot()['entities'] if row['id'] == 'approval:pending-exclusive')
        self.assertEqual(approval['data']['status'], 'PENDING')

    @unittest.skipUnless(find_spec('tripmate.planning'), 'Merge B04 for actual pricing/Planning integration')
    def test_actual_b04_and_planning_consume_portal_cloud_offer_bundles(self):
        import tempfile
        from tripmate.supplier.gateway import SupplierGateway
        from tripmate.fixtures.b03 import fixture_quotes
        from tripmate.planning.fixtures import fixture_runtime
        from tripmate.agents.planning import TravelPlanningAgent
        self.server.app.supplier = SupplierGateway(self.server.app.operations,
                                                   policy=PricingPolicy('0.10', '0.00', 'integration-policy-1'))
        supplier_browser = self.browser
        self.login(self.operator)
        operator_browser = self.browser
        for quote in fixture_quotes():
            self.browser = supplier_browser
            offer = quote['offer']
            payload = {key: deepcopy(offer[key]) for key in SOURCE_FIELDS if key != 'supplierId'}
            payload.update(offerReference=offer['offerId'], sourceReference='synthetic://b03/' + offer['offerId'],
                           commercialTerms=[], product={key: deepcopy(value) for key, value in quote['product'].items()
                                                         if key not in {'productId', 'sourceIds'}})
            case_id = self.assess(payload)
            self.browser = operator_browser
            _, result = self.action(case_id)
            self.assertEqual(result[0], 200, result)
            self.assertEqual(result[1]['status'], 'APPROVED')
        with tempfile.TemporaryDirectory() as folder:
            case, _, planning = fixture_runtime(database=str(Path(folder) / 'planning.sqlite3'))
            planning.offers = self.server.app.supplier
            try:
                result = TravelPlanningAgent(planning).handle_case(case)
                self.assertEqual(result['status'], 'SUCCESS', result)
            finally:
                planning.repository.close()


if __name__ == '__main__':
    unittest.main()
