"""B08 records over the existing private Operations repository/RPC boundary."""
from copy import deepcopy
from tripmate.contracts import validate
from .common import SupplierError


class SharedSupplierRepository:
    def __init__(self, repository):
        self.repository = repository

    @staticmethod
    def key(offer_id, version):
        return str(version) + '/' + offer_id

    def reserve(self, offer_id, case_id, mode, supplier_id=None):
        with self.repository.transaction() as records:
            previous = records.get('supplier_current', offer_id)
            if previous:
                if previous['supplierId'] != supplier_id:
                    raise SupplierError('ACCESS_DENIED', 'Offer ownership cannot change')
                if previous['executionMode'] != mode:
                    raise SupplierError('VERIFICATION_FAILED', 'Fixture and real identities cannot mix')
            version = previous['version'] + 1 if previous else 1
            records.put('supplier_current', offer_id, dict(offerId=offer_id, version=version,
                        caseId=case_id, supplierId=supplier_id, executionMode=mode))
            records.put('supplier_version', self.key(offer_id, version),
                        dict(offer=None, price=None, result=None, caseId=case_id,
                             supplierId=supplier_id, executionMode=mode, storageRevision=0))
        return version

    def save(self, offer_id, version, record):
        with self.repository.transaction() as records:
            pointer = records.get('supplier_current', offer_id)
            if not pointer or pointer.get('invalidated') or pointer['version'] != version or record['supplierId'] != pointer['supplierId']:
                raise SupplierError('INVALID_CONTRACT', 'A newer source revision superseded this assessment')
            current = records.get('supplier_version', self.key(offer_id, version))
            expected = record.get('storageRevision', 0)
            if current.get('storageRevision', 0) != expected:
                raise SupplierError('INVALID_CONTRACT', 'Offer state changed; reload before recording another decision')
            saved = deepcopy(record)
            saved['storageRevision'] = expected + 1
            records.put('supplier_version', self.key(offer_id, version), saved)

    def current(self, offer_id):
        with self.repository.transaction() as records:
            pointer = records.get('supplier_current', offer_id)
            value = records.get('supplier_version', self.key(offer_id, pointer['version'])) if pointer else None
            return dict(value, offer=None, price=None, result=None, invalidated=True) if value and pointer.get('invalidated') else value

    def records(self):
        with self.repository.transaction() as records:
            return [records.get('supplier_version', self.key(pointer['offerId'], pointer['version']))
                    for pointer in records.all('supplier_current') if not pointer.get('invalidated')]

    def history(self, offer_id):
        pointer = self.repository.read('supplier_current', offer_id)
        return [self.repository.read('supplier_version', self.key(offer_id, version))
                for version in range(1, pointer['version'] + 1)] if pointer else []


class SharedApprovals:
    """Append-only pending/decision records; conflicting decisions are rejected."""
    def __init__(self, repository):
        self.repository = repository

    def save(self, approval):
        validate('Approval', approval)
        key = approval['approvalId'] + '/' + approval['status']
        with self.repository.transaction() as records:
            existing = records.get('supplier_approval', key)
            if existing and existing != approval:
                raise SupplierError('APPROVAL_REJECTED', 'This approval already has a different recorded decision')
            records.put('supplier_approval', key, deepcopy(approval))

    def find_by_subject(self, ref):
        return [item for item in self.repository.list('supplier_approval') if item['subject'] == ref]
