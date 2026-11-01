"""Cloud workflow regressions: read-only membership, lookup cost and late workers."""
from copy import deepcopy
from threading import Event
import unittest
from unittest.mock import patch

from test_portals import FakeCloud
from tripmate.operations.common import OperationsError
from tripmate.portal.server import Portal


class CloudWorkflowTests(unittest.TestCase):
    def test_membership_display_reads_current_evidence_without_transaction_or_audit_write(self):
        class ReadOnlyCloud(FakeCloud):
            def rpc(self, name, body=None):
                if name in {'tripmate_state', 'tripmate_snapshot', 'tripmate_commit'}:
                    raise AssertionError('Displaying membership must not require a write transaction')
                return super().rpc(name, body)
        cloud = ReadOnlyCloud()
        actor, _ = cloud.add()
        cloud.accounts[actor].update(membership='PAID', paidUntil='2099-01-01T00:00:00Z')
        app = Portal(cloud)
        before = deepcopy(cloud.state)
        for tier in ('PAID', 'FREE'):
            cloud.accounts[actor]['membership'] = tier
            with app.operations.repository.scope():
                view = app.operations.premium(actor, 'same-display-key', 'MEMBERSHIP')
            self.assertEqual(view['decision']['outcome'], 'ALLOWED')
            self.assertEqual(view['decision']['membershipLevel'], tier)
        self.assertEqual(cloud.state, before)

    def test_timed_out_worker_cannot_commit_after_its_slow_read_completes(self):
        reading, release, finished = Event(), Event(), Event()
        class SlowCloud(FakeCloud):
            def rpc(self, name, body=None):
                if name == 'tripmate_state':
                    reading.set()
                    if not release.wait(2):
                        raise RuntimeError('Test read was not released')
                return super().rpc(name, body)
        cloud = SlowCloud()
        app = Portal(cloud)
        app.operations.dependency_timeout = 0.05
        errors = []
        def late_write():
            try:
                with app.operations.repository.transaction() as rows:
                    rows.put('test', 'late', {'saved': True})
            except OperationsError as exc:
                errors.append(exc.code)
                raise
            finally:
                finished.set()
        try:
            with self.assertRaises(TimeoutError):
                app.operations._dependency(late_write)
            self.assertTrue(reading.is_set())
        finally:
            release.set()
        self.assertTrue(finished.wait(2))
        self.assertIsNone(app.operations.repository.read('test', 'late'))
        self.assertEqual(cloud.state['version'], 0)
        self.assertEqual(errors, ['TOOL_UNAVAILABLE'])

    def test_offer_lookup_reads_case_statuses_once_and_still_excludes_withdrawals(self):
        from test_planning_portal import PlanningPortalTests
        fixture = PlanningPortalTests()
        self.addCleanup(fixture.doCleanups)
        fixture.setUp()
        with patch.object(fixture.cloud, 'rpc', wraps=fixture.cloud.rpc) as rpc, \
             fixture.app.operations.repository.scope():
            quotes = fixture.app.supplier.find_selectable({}, fixture.app.operations.clock())
        self.assertEqual(len(quotes), 4)
        case_reads = [call for call in rpc.call_args_list if call.args[0] == 'tripmate_read_records'
                      and call.args[1]['record_kind'] == 'case']
        self.assertEqual(len(case_reads), 1)
        self.assertNotIn('record_id', case_reads[0].args[1])
        case_id = quotes[0]['offer']['caseId']
        with fixture.app.operations.repository.transaction() as rows:
            rec = rows.get('case', case_id)
            rec['case']['status'] = 'WITHDRAWN'
            rows.put('case', case_id, rec)
        with fixture.app.operations.repository.scope():
            current = fixture.app.supplier.find_selectable({}, fixture.app.operations.clock())
        self.assertEqual(len(current), 3)
        self.assertNotIn(case_id, {quote['offer']['caseId'] for quote in current})

    def test_model_portal_has_bounded_time_for_cloud_io_as_well_as_model_call(self):
        with patch.dict('os.environ', {'ELEC5620_API_KEY': 'test-only',
                                     'TRIPMATE_LLM_PROVIDER': 'elec5620'}, clear=True), \
             patch('tripmate.adapters.campus.CampusClient'):
            self.assertEqual(Portal(FakeCloud(), model_planning=True).operations.dependency_timeout, 60)
            self.assertEqual(Portal(FakeCloud()).operations.dependency_timeout, 30)
