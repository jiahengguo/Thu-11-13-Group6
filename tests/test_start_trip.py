"""Traveller-confirmed activation, current entitlement and immutable plan history."""
import unittest
from copy import deepcopy
from uuid import uuid4

import test_planning_portal as planning_tests
from tripmate.portal.server import Portal


class StartTripTests(unittest.TestCase):
    def setUp(self):
        self.fixture = planning_tests.PlanningPortalTests()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.setUp()
        self.f = self.fixture
        cid, self.ids, result = self.f.generate()
        self.cid = cid
        self.f.release(cid, result['revision'])
        self.version = self.f.app.planning.get_version(self.ids[0])['version']
        self.assertEqual(self.f.adopt(self.ids[0])[0][0], 200)

    def start(self, actor=None, version=None, confirmed=True, key=None):
        body = dict(requestKey=key or str(uuid4()), versionId=version or self.ids[0], confirmed=confirmed)
        return self.f.clients[actor or self.f.traveller].call('/api/operations/start-trip', body), body

    def current(self):
        return self.f.app.operations.repository.read('lifecycle', self.version['planId'])

    def test_explicit_start_persists_once_and_allows_disruption_confirmation(self):
        self.assertEqual(self.current()['planStatus'], 'PLANNED')
        fields = dict(planId=self.version['planId'], details='Simulated cancellation reported by traveller.')
        intents = [dict(caseType='DISRUPTION', fields=fields)]
        client = self.f.clients[self.f.traveller]
        status, intake, _ = client.call('/api/operations/intake', dict(requestKey=str(uuid4()), text='Cancellation', intents=intents))
        self.assertEqual(status, 200)
        status, _, _ = client.call('/api/operations/confirm', dict(requestKey=str(uuid4()), intakeId=intake['id'],
                                    revision=intake['revision'], intents=intents, confirmed=True))
        self.assertEqual(status, 403)
        original = deepcopy(self.f.app.planning.get_version(self.ids[0]))
        result, body = self.start()
        self.assertEqual(result[0], 200, result[1])
        self.assertTrue(result[1]['started'])
        self.assertEqual(self.current()['planStatus'], 'ACTIVE')
        self.assertIn('startedAt', self.current())
        after = deepcopy(self.f.cloud.state)
        self.assertEqual(client.call('/api/operations/start-trip', body)[1], result[1])
        self.assertEqual(self.f.cloud.state, after)
        traces = len(after['traces'])
        self.assertEqual(self.start()[0][1]['planStatus'], 'ACTIVE')
        self.assertEqual(len(self.f.cloud.state['traces']), traces)
        self.assertEqual(self.f.app.planning.get_version(self.ids[0]), original)
        restarted = Portal(self.f.cloud, supplier_policy=self.f.policy)
        self.assertEqual(restarted.operations.trips(self.f.traveller)[0]['planStatus'], 'ACTIVE')
        self.f.confirm(self.f.traveller, 'DISRUPTION', fields)

    def test_unconfirmed_unadopted_stale_and_cross_user_activation_are_rejected(self):
        before = deepcopy(self.f.cloud.state)
        for options in (dict(confirmed=False), dict(version=self.ids[1]), dict(actor=self.f.other), dict(actor=self.f.operator)):
            with self.subTest(options=options):
                self.assertNotEqual(self.start(**options)[0][0], 200)
                self.assertEqual(self.f.cloud.state, before)

    def test_current_membership_denial_is_recorded_without_activation(self):
        with self.f.app.operations.repository.transaction() as rows:
            for i in range(2):
                rows.put('lifecycle', 'extra-' + str(i), dict(planId='extra-' + str(i), travellerId=self.f.traveller,
                         selectedVersionId='other-version-' + str(i), planStatus='PLANNED'))
        result, _ = self.start()
        self.assertEqual(result[0], 200, result[1])
        self.assertFalse(result[1]['started'])
        self.assertEqual(result[1]['decision']['outcome'], 'DENIED')
        self.assertEqual(self.current()['planStatus'], 'PLANNED')
        rec = self.f.app.operations.repository.read('case', self.cid)
        self.assertEqual(rec['membershipSnapshots'][-1]['action'], 'START_TRIP')
        self.assertEqual(rec['membershipSnapshots'][-1]['outcome'], 'DENIED')

    def test_failed_save_has_no_active_state_or_trace_and_same_request_can_retry(self):
        before = deepcopy(self.f.cloud.state)
        self.f.cloud.fail_commit = True
        result, body = self.start()
        self.assertNotEqual(result[0], 200)
        self.assertEqual(self.f.cloud.state, before)
        self.f.cloud.fail_commit = False
        self.assertEqual(self.f.clients[self.f.traveller].call('/api/operations/start-trip', body)[1]['planStatus'], 'ACTIVE')

    def test_adopting_revision_preserves_active_status_and_original_start(self):
        self.assertEqual(self.start()[0][1]['planStatus'], 'ACTIVE')
        started_at = self.current()['startedAt']
        cid, revised, result = self.f.generate(self.ids[0], budget='850.00')
        self.f.release(cid, result['revision'])
        self.assertEqual(self.f.adopt(revised[0], self.ids[0])[0][0], 200)
        self.assertEqual(self.current()['planStatus'], 'ACTIVE')
        self.assertEqual(self.current()['selectedVersionId'], revised[0])
        self.assertEqual(self.current()['startedAt'], started_at)
        before = deepcopy(self.f.cloud.state)
        # An old accepted proposal must not overwrite the newer current lifecycle.
        self.assertNotEqual(self.f.adopt(self.ids[0])[0][0], 200)
        self.assertEqual(self.f.cloud.state, before)
        self.assertNotEqual(self.start(version=self.ids[0])[0][0], 200)
