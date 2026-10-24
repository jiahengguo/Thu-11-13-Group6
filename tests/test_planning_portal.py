"""Authenticated Supplier -> Planning -> reviewed delivery -> atomic adoption."""
import json
import threading
import unittest
from copy import deepcopy
from uuid import uuid4

from test_portals import Browser, FakeCloud
from tripmate.fixtures.b03 import fixture_quotes, FIXTURE_TIME
from tripmate.portal.server import make_server, Portal
from tripmate.supplier.common import PricingPolicy, SOURCE_FIELDS
from tripmate.planning.common import PlanningError


class PlanningPortalTests(unittest.TestCase):
    def setUp(self):
        self.cloud = FakeCloud()
        self.traveller, _ = self.cloud.add()
        self.other, _ = self.cloud.add()
        self.supplier, _ = self.cloud.add('SUPPLIER')
        self.operator, _ = self.cloud.add('OPERATOR')
        self.policy = PricingPolicy('0.10', '15.00', 'demo-2026-10-24')
        self.server = make_server(self.cloud, port=0, supplier_policy=self.policy)
        self.app = self.server.app
        self.app.operations.clock = lambda: FIXTURE_TIME
        self.app.operations.entitlement.clock = lambda: FIXTURE_TIME
        self.app.supplier.runtime.clock = lambda: FIXTURE_TIME
        self.app.supplier.pricing.clock = lambda: FIXTURE_TIME
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop)
        self.root = 'http://127.0.0.1:' + str(self.server.server_port)
        self.clients = {}
        for actor in (self.traveller, self.other, self.supplier, self.operator):
            client = Browser(self.root)
            self.assertEqual(client.login(actor)[0], 200)
            self.clients[actor] = client
        self.seed_offers()

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def post(self, actor, action, body):
        status, data, _ = self.clients[actor].call('/api/operations/' + action, dict(body, requestKey=str(uuid4())))
        self.assertEqual(status, 200, data)
        return data

    def confirm(self, actor, case_type, fields):
        intents = [dict(caseType=case_type, fields=fields)]
        intake = self.post(actor, 'intake', dict(text='Explicitly confirmed simulated request.', intents=intents))
        confirmed = self.post(actor, 'confirm', dict(intakeId=intake['id'], revision=intake['revision'],
                                                    intents=intents, confirmed=True))
        return confirmed['caseIds'][0]

    def seed_offers(self):
        for quote in fixture_quotes():
            if quote['offer']['offerId'] not in ('coach', 'express', 'basic-stay', 'walk'):
                continue
            source = quote['offer']
            submission = {key: deepcopy(source[key]) for key in SOURCE_FIELDS if key != 'supplierId'}
            # Explicit test inventory meets the authorised demo policy, including activities.
            submission.update(supplierCost=dict(amount='180.00', currency='AUD'), commercialTerms=[],
                              offerReference=source['offerId'], sourceReference='synthetic://portal/' + source['offerId'],
                              product={key: deepcopy(value) for key, value in quote['product'].items()
                                       if key not in ('productId', 'sourceIds')})
            cid = self.confirm(self.supplier, 'OFFER', dict(details='Simulated service package.', supplierOffer=submission))
            dispatched = self.post(self.supplier, 'dispatch', dict(caseId=cid, revision=1))
            assessment = self.clients[self.operator].call('/api/supplier/assessment?caseId=' + cid)[1]
            status, data, _ = self.clients[self.operator].call('/api/supplier/review', dict(
                caseId=cid, revision=dispatched['revision'], materialVersion=assessment['offer']['materialVersion'],
                decision='PASS', reason='Checked source and configured simulated prices.', requestKey=str(uuid4())))
            self.assertEqual(status, 200, data)
            self.assertEqual(data['status'], 'APPROVED', data)

    def generate(self, baseline=None, budget='900.00'):
        fields = dict(origin='Sydney Central', destination='Melbourne Centre', partySize=1,
                      budgetCeiling=dict(amount=budget, currency='AUD'),
                      travelDates=dict(startDate='2026-10-20', endDate='2026-10-22'),
                      rankingMode='VALUE', preferences=[], constraints=[])
        if baseline:
            fields['baselineVersionId'] = baseline
        cid = self.confirm(self.traveller, 'PLAN_REVISION' if baseline else 'TRAVEL_PLANNING', fields)
        result = self.post(self.traveller, 'dispatch', dict(caseId=cid, revision=1))
        self.assertEqual(result['case']['status'], 'UNDER_REVIEW', result)
        record = self.app.operations.repository.read('case', cid)
        ids = [ref['subjectId'] for ref in record['specialistResult']['subjects']]
        return cid, ids, result

    def release(self, cid, revision):
        reviewed = self.post(self.operator, 'review', dict(caseId=cid, revision=revision, decision='APPROVE',
                               reason='Checked the shared Planning review and response.'))
        self.post(self.traveller, 'deliver', dict(caseId=cid, revision=reviewed['revision']))
        return self.clients[self.traveller].call('/api/operations/case?caseId=' + cid)[1]

    def adopt(self, vid, baseline=None, key=None):
        body = dict(versionId=vid, expectedBaseline=baseline, accepted=True, requestKey=key or str(uuid4()))
        return self.clients[self.traveller].call('/api/operations/adopt', body), body

    def test_authenticated_plan_options_adoption_revision_and_restart(self):
        cid, ids, result = self.generate()
        self.assertGreater(len(ids), 1)
        self.assertNotIn('planVersionIds', result)
        self.assertNotEqual(self.clients[self.traveller].call('/api/operations/plan?versionId=' + ids[0])[0], 200)
        released = self.release(cid, result['revision'])
        self.assertEqual(released['planVersionIds'], ids)
        status, public, _ = self.clients[self.traveller].call('/api/operations/plan?versionId=' + ids[0])
        self.assertEqual(status, 200, public)
        self.assertEqual(public['version']['review']['policyVersion'], 'shared-deterministic-review-1')
        self.assertEqual(public['version']['totalPrice']['amount'], '594.00')
        self.assertNotIn('supplierCost', json.dumps(public))
        self.assertNotIn('quotes', public)
        self.assertEqual(self.clients[self.other].call('/api/operations/plan?versionId=' + ids[0])[0], 403)
        original = self.app.planning.get_version(ids[0])
        adopted, body = self.adopt(ids[0])
        self.assertEqual(adopted[0], 200, adopted[1])
        self.assertEqual(self.clients[self.traveller].call('/api/operations/adopt', body)[1], adopted[1])
        self.assertEqual(self.app.planning.get_version(ids[0]), original)
        self.assertEqual(self.adopt(ids[1])[0][0], 422)
        self.seed_offers()  # Current supplier material versions refresh; baseline remains immutable.
        revision_cid, revised_ids, revision = self.generate(ids[0], budget='850.00')
        self.release(revision_cid, revision['revision'])
        comparison = self.clients[self.traveller].call('/api/operations/plan?versionId=' + revised_ids[0])[1]
        self.assertIn('budgetCeiling', comparison['comparison']['changedRequirements'])
        self.assertTrue(comparison['comparison']['itineraryChanges'])
        self.assertTrue(all(item['before']['offerVersion'] == 1 and item['after']['offerVersion'] == 2
                            for item in comparison['comparison']['itineraryChanges']))
        self.assertNotIn('supplierCost', json.dumps(comparison))
        self.assertEqual(self.adopt(revised_ids[0], ids[0])[0][0], 200)
        restarted = Portal(self.cloud, supplier_policy=self.policy)
        self.assertEqual(restarted.planning.selected(original['version']['planId']), revised_ids[0])
        self.assertEqual(restarted.planning.get_version(ids[0]), original)
        trace = self.app.operations.traces(self.operator, cid)
        self.assertEqual(len(trace), len({event['eventId'] for event in trace}))
        self.assertTrue(any(event['actor'] == 'planning' for event in trace))

    def test_adoption_cloud_failure_rolls_back_selection_lifecycle_and_audit(self):
        cid, ids, result = self.generate()
        self.release(cid, result['revision'])
        before = deepcopy(self.cloud.state)
        self.cloud.fail_commit = True
        adopted, body = self.adopt(ids[0])
        self.assertNotEqual(adopted[0], 200)
        self.assertEqual(self.cloud.state, before)
        self.cloud.fail_commit = False
        self.assertIsNone(self.app.planning.selected(self.app.planning.get_version(ids[0])['version']['planId']))
        self.assertEqual(self.clients[self.traveller].call('/api/operations/adopt', body)[0], 200)

    def test_changed_supplier_source_blocks_adoption_and_forged_review(self):
        cid, ids, result = self.generate()
        self.release(cid, result['revision'])
        version = self.app.planning.get_version(ids[0])['version']
        with self.app.operations.repository.transaction() as rows:
            pointer = rows.get('supplier_current', version['items'][0]['offerId'])
            rows.put('supplier_current', version['items'][0]['offerId'], dict(pointer, invalidated=True))
        before = deepcopy(self.cloud.state)
        self.assertNotEqual(self.adopt(ids[0])[0][0], 200)
        self.assertEqual(self.cloud.state, before)
        from tripmate.planning.review import planning_reviewer
        checked = planning_reviewer(self.app.operations, self.app.supplier).review(
            version, version['sourceReferences'], ['planning-1.0'])
        self.assertEqual(checked['outcome'], 'REVISION_REQUIRED')

    def test_no_inventory_cannot_substitute_demo_catalog(self):
        with self.app.operations.repository.transaction() as rows:
            for pointer in rows.all('supplier_current'):
                rows.put('supplier_current', pointer['offerId'], dict(pointer, invalidated=True))
        self.app.fixtures.reset()
        fields = dict(origin='Sydney Central', destination='Melbourne Centre', partySize=1,
                      budgetCeiling=dict(amount='900.00', currency='AUD'),
                      travelDates=dict(startDate='2026-10-20', endDate='2026-10-22'), rankingMode='VALUE')
        cid = self.confirm(self.traveller, 'TRAVEL_PLANNING', fields)
        result = self.post(self.traveller, 'dispatch', dict(caseId=cid, revision=1))
        self.assertEqual(result['case']['status'], 'HUMAN_ASSISTANCE')
        self.assertIsNone(result['response'])
        self.assertNotIn('planVersionIds', result)

    def test_immutable_run_cannot_be_overwritten(self):
        cid, ids, _ = self.generate()
        run = self.app.operations.repository.read('case', cid)['specialistResult']
        before = deepcopy(self.cloud.state)
        with self.assertRaises(PlanningError):
            self.app.planning.save_run(run, [self.app.planning.get_version(ids[0])], [])
        self.assertEqual(self.cloud.state, before)
