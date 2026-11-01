"""Adopted route privacy and entitlement through authenticated HTTP."""
import unittest
from uuid import uuid4
import test_planning_portal as planning

class TripMapTests(unittest.TestCase):
    setUp = planning.PlanningPortalTests.setUp
    stop = planning.PlanningPortalTests.stop
    seed_offers = planning.PlanningPortalTests.seed_offers
    post = planning.PlanningPortalTests.post
    confirm = planning.PlanningPortalTests.confirm
    generate = planning.PlanningPortalTests.generate
    release = planning.PlanningPortalTests.release
    adopt = planning.PlanningPortalTests.adopt

    def prepare(self):
        cid,ids,result=self.generate()
        self.release(cid,result['revision'])
        self.adopt(ids[0])
        self.cloud.accounts[self.traveller].update(membership='PAID',paidUntil='2099-01-01T00:00:00Z')
        return ids[0]

    def call_map(self, actor, version, key=None):
        return self.clients[actor].call('/api/operations/premium',dict(requestKey=key or str(uuid4()),action='ROUTE_MAP',versionId=version))

    def test_map_uses_owned_adopted_version_and_hides_costs(self):
        version=self.prepare()
        status,result,*_=self.call_map(self.traveller,version)
        self.assertEqual(status,200,result)
        self.assertEqual(result['versionId'],version)
        self.assertTrue(result['routePoints'])
        record=self.app.planning.get_version(version)['version']
        self.assertEqual({p['itemId'] for p in result['routePoints']},{i['itemId'] for i in record['items']})
        self.assertNotIn('supplierCost',str(result))
        self.assertTrue(result['simulationOnly'])

    def test_other_user_and_operator_cannot_read_route(self):
        version=self.prepare()
        for actor in (self.other,self.operator,self.supplier):
            self.assertEqual(self.call_map(actor,version)[0],403)

    def test_expired_membership_cannot_replay_map(self):
        version=self.prepare();key=str(uuid4())
        self.assertIn('routePoints',self.call_map(self.traveller,version,key)[1])
        self.cloud.accounts[self.traveller].update(paidUntil='2020-01-01T00:00:00Z')
        result=self.call_map(self.traveller,version,key)[1]
        self.assertEqual(result['decision']['outcome'],'DENIED')
        self.assertNotIn('routePoints',result)

    def test_unreleased_or_unadopted_version_is_blocked(self):
        cid,ids,result=self.generate()
        self.cloud.accounts[self.traveller].update(membership='PAID',paidUntil='2099-01-01T00:00:00Z')
        self.assertNotEqual(self.call_map(self.traveller,ids[0])[0],200)
        self.release(cid,result['revision'])
        self.assertNotEqual(self.call_map(self.traveller,ids[0])[0],200)

    def test_provider_failure_does_not_return_sample_map(self):
        version=self.prepare()
        def unavailable(_):
            raise OSError('isolated route provider unavailable')
        self.app.operations.benefits.route_for_version=unavailable
        status,data,*_=self.call_map(self.traveller,version)
        self.assertEqual(status,503)
        self.assertNotIn('routePoints',data)
