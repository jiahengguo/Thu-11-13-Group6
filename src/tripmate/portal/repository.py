"""Persist the existing Operations contracts in atomic, backend-only Supabase RPCs.

Optimistic database revision rejects concurrent changes; callbacks are never replayed.
Private snapshots are server-side only. This adapter targets the teaching workload.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
from tripmate.contracts import validate
from tripmate.operations.common import OperationsError


class CloudRecords:
    def __init__(self, snapshot):
        self.data = {(r['kind'], r['id']): r['payload'] for r in snapshot['records']}
        self.writes, self.events = {}, []

    @contextmanager
    def savepoint(self):
        """Undo a failed specialist import before recording the coordinator failure."""
        before = deepcopy((self.data, self.writes, self.events))
        try:
            yield
        except Exception:
            self.data, self.writes, self.events = before
            raise

    def get(self, kind, key):
        return deepcopy(self.data.get((kind, key)))

    def all(self, kind):
        return [deepcopy(v) for (k, _), v in self.data.items() if k == kind]

    def put(self, kind, key, payload):
        self.data[kind, key] = deepcopy(payload)
        self.writes[kind, key] = {'kind': kind, 'id': key, 'payload': deepcopy(payload)}

    def trace(self, event):
        validate('TraceEvent', event)
        self.events.append(deepcopy(event))


class SupabaseOperationsRepository:
    def __init__(self, cloud):
        self.cloud = cloud
        self.context = ContextVar('tripmate_cloud_request', default=None)

    @contextmanager
    def scope(self):
        token = self.context.set({'profiles': {}})
        try:
            yield
        finally:
            self.context.reset(token)

    def snapshot(self):
        context = self.context.get()
        if context is None:
            return self.cloud.rpc('tripmate_state')
        if 'snapshot' not in context:
            context['snapshot'] = self.cloud.rpc('tripmate_state')
        return context['snapshot']

    def read(self, kind, key):
        if kind == 'profile':
            try:
                context = self.context.get()
                if context is None:
                    return self.cloud.profile(key)
                if key not in context['profiles']:
                    context['profiles'][key] = self.cloud.profile(key)
                return deepcopy(context['profiles'][key])
            except OperationsError as exc:
                if exc.code == 'ACCESS_DENIED':
                    return None
                raise
        if key is None:
            return None
        rows = self._scoped_read('tripmate_read_records', {'record_kind': kind, 'record_id': key})
        return deepcopy(rows[0]) if rows else None

    def list(self, kind):
        if kind == 'profile':
            raise OperationsError('ACCESS_DENIED', 'Identity enumeration is unavailable in the authenticated portal.')
        return deepcopy(self._scoped_read('tripmate_read_records', {'record_kind': kind}))

    def _scoped_read(self, name, body):
        context = self.context.get()
        if context is None:
            return self.cloud.rpc(name, body)
        reads = context.setdefault('reads', {})
        key = (name, tuple(sorted(body.items())))
        if key not in reads:
            reads[key] = self.cloud.rpc(name, body)
        return reads[key]

    def _commit(self, snapshot, records, entry=None):
        if records.writes or records.events or entry:
            self.cloud.rpc('tripmate_commit', {'expected_version': snapshot['version'], 'writes': list(records.writes.values()), 'events': records.events, 'command_entry': entry})
            context = self.context.get()
            if context is not None:
                context.pop('snapshot', None)
                context.pop('reads', None)

    @contextmanager
    def transaction(self):
        snapshot = self.snapshot()
        records = CloudRecords(snapshot)
        yield records
        self._commit(snapshot, records)

    def command(self, key, fingerprint, callback):
        snapshot = self.snapshot()
        previous = next((c for c in snapshot['commands'] if c['key'] == key), None)
        if previous:
            if previous['fingerprint'] != fingerprint:
                raise OperationsError('UNCONFIRMED_REQUEST', 'This operation ID was used for different content.')
            return previous['result']
        records = CloudRecords(snapshot)
        result = callback(records)
        self._commit(snapshot, records, {'key': key, 'fingerprint': fingerprint, 'result': result})
        return result

    def cached(self, key, fingerprint):
        previous = next((c for c in self.snapshot()['commands'] if c['key'] == key), None)
        if previous and previous['fingerprint'] != fingerprint:
            raise OperationsError('UNCONFIRMED_REQUEST', 'This operation ID was used for different content.')
        return (True, previous['result']) if previous else (False, None)

    def find_by_case(self, case_id):
        return deepcopy(self._scoped_read('tripmate_read_traces', {'requested_case': case_id}))

    def append(self, event):
        with self.transaction() as records:
            records.trace(event)


class NoUserFixtures:
    def list_entities(self, kind):
        return []

    def snapshot(self):
        return {'entities': [], 'relations': []}
