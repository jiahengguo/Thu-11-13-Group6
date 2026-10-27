"""Private durable investigation snapshots; Operations imports traces atomically."""
from tripmate.contracts import validate
from tripmate.operations.common import OperationsError, instant


class SharedExceptionRepository:
    def __init__(self, repository):
        self.repository = repository

    def save(self, snapshot):
        validate('AgentResult', snapshot['result'])
        for event in snapshot['trace']:
            validate('TraceEvent', event)
        for approval in snapshot['approvals']:
            validate('Approval', approval)
        try:
            with self.repository.transaction() as rows:
                run_id = snapshot['result']['runId']
                if rows.get('exception_saved_run', run_id) is not None:
                    raise OSError('An immutable investigation already exists.')
                proposal = snapshot.get('proposal')
                if proposal:
                    previous = [r for r in rows.all('exception_saved_run')
                                if r['result']['caseId'] == snapshot['result']['caseId'] and r.get('proposal')]
                    latest = max(previous, key=lambda r: r['proposal']['subject']['materialVersion']) if previous else None
                    if proposal['previousSubject'] != (latest['proposal']['subject'] if latest else None):
                        raise OSError('A newer investigation superseded this attempt.')
                rows.put('exception_saved_run', run_id, snapshot)
        except OperationsError:
            # The existing runtime treats OSError as persistence failure and never
            # releases a successful result for an unsaved investigation.
            raise OSError('Investigation storage could not commit.') from None

    def get(self, run_id):
        return self.repository.read('exception_saved_run', run_id)

    def recent(self):
        return sorted(self.repository.list('exception_saved_run'), key=lambda r: instant(r['recordedAt']), reverse=True)[:30]

    def latest_proposal(self, case_id):
        records = [r for r in self.repository.list('exception_saved_run')
                   if r['result']['caseId'] == case_id and r.get('proposal')]
        return max(records, key=lambda r: r['proposal']['subject']['materialVersion']) if records else None

    def find_by_case(self, case_id):
        return [event for r in self.repository.list('exception_saved_run') if r['result']['caseId'] == case_id
                for event in r['trace']]
