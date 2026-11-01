"""Single-record reads must not download the entire cloud transaction snapshot."""
from copy import deepcopy
import unittest

from test_portals import FakeCloud
from tripmate.planning.common import PlanningError
from tripmate.planning.shared_repository import SharedPlanningRepository
from tripmate.portal.repository import SupabaseOperationsRepository
from tripmate.supplier.shared_repository import SharedSupplierRepository


class ReadOnlyCloud(FakeCloud):
    def rpc(self, name, body=None):
        if name in {'tripmate_state', 'tripmate_snapshot', 'tripmate_commit'}:
            raise AssertionError('A single-record read must use the scoped reader')
        return super().rpc(name, body)


class ScopedCloudReadTests(unittest.TestCase):
    def seed(self, cloud, kind, key, payload):
        cloud.state['records'].append(dict(kind=kind, id=key, payload=deepcopy(payload)))

    def test_planning_version_selection_and_acceptance_use_scoped_reads(self):
        cloud = ReadOnlyCloud()
        self.seed(cloud, 'planning_version', 'v1', {'version': {'versionId': 'v1'}})
        self.seed(cloud, 'planning_selected', 'p1', {'versionId': 'v1'})
        self.seed(cloud, 'planning_acceptance', 'v1', {'versionId': 'v1'})
        before = deepcopy(cloud.state)
        planning = SharedPlanningRepository(SupabaseOperationsRepository(cloud))
        self.assertEqual(planning.get_version('v1'), {'version': {'versionId': 'v1'}})
        self.assertEqual(planning.selected('p1'), 'v1')
        self.assertEqual(planning.accepted('v1'), planning.get_version('v1'))
        self.assertEqual(cloud.state, before)

    def test_missing_planning_pointers_and_version_keep_existing_failure_behavior(self):
        planning = SharedPlanningRepository(SupabaseOperationsRepository(ReadOnlyCloud()))
        self.assertIsNone(planning.selected('missing'))
        self.assertIsNone(planning.accepted('missing'))
        with self.assertRaises(PlanningError) as caught:
            planning.get_version('missing')
        self.assertEqual(caught.exception.code, 'MISSING_REQUIRED_FIELDS')

    def test_adoption_reads_its_own_uncommitted_records(self):
        cloud = FakeCloud()
        repository = SupabaseOperationsRepository(cloud)
        planning = SharedPlanningRepository(repository)
        before = deepcopy(cloud.state)
        with self.assertRaisesRegex(RuntimeError, 'Rollback synthetic adoption'):
            with repository.transaction() as rows:
                record = {'version': {'versionId': 'pending'}}
                rows.put('planning_version', 'pending', record)
                rows.put('planning_selected', 'p1', {'versionId': 'pending'})
                rows.put('planning_acceptance', 'pending', {'versionId': 'pending'})
                actual = planning.adopt_atomically(rows, lambda: (
                    planning.get_version('pending'), planning.selected('p1'), planning.accepted('pending')))
                self.assertEqual(actual, (record, 'pending', record))
                raise RuntimeError('Rollback synthetic adoption')
        self.assertEqual(cloud.state, before)

    def test_supplier_current_uses_scoped_reads_and_preserves_invalidation(self):
        cloud = ReadOnlyCloud()
        self.seed(cloud, 'supplier_current', 'o1', {'offerId': 'o1', 'version': 1})
        record = {'offer': {'offerId': 'o1'}, 'price': {'amount': '198.00'}, 'result': {'status': 'SUCCESS'}}
        self.seed(cloud, 'supplier_version', '1/o1', record)
        supplier = SharedSupplierRepository(SupabaseOperationsRepository(cloud))
        self.assertEqual(supplier.current('o1'), record)
        cloud.state['records'][0]['payload']['invalidated'] = True
        before = deepcopy(cloud.state)
        invalidated = supplier.current('o1')
        self.assertTrue(invalidated['invalidated'])
        self.assertIsNone(invalidated['offer'])
        self.assertIsNone(invalidated['price'])
        self.assertIsNone(invalidated['result'])
        self.assertEqual(cloud.state, before)

    def test_supplier_missing_pointer_and_missing_version_return_none(self):
        cloud = ReadOnlyCloud()
        supplier = SharedSupplierRepository(SupabaseOperationsRepository(cloud))
        self.assertIsNone(supplier.current('missing'))
        self.seed(cloud, 'supplier_current', 'o1', {'offerId': 'o1', 'version': 1})
        self.assertIsNone(supplier.current('o1'))
