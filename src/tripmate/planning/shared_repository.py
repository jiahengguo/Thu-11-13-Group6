"""Immutable Planning records over the existing private Operations repository."""
from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy

from tripmate.contracts import validate
from .common import PlanningError, uid


class SharedPlanningRepository:
    def __init__(self, repository):
        self.repository = repository
        self.bound_records = ContextVar('planning_adoption_records', default=None)

    @contextmanager
    def records(self):
        bound = self.bound_records.get()
        if bound is not None:
            yield bound
        else:
            with self.repository.transaction() as rows:
                yield rows

    def adopt_atomically(self, rows, callback):
        """Join the coordinator command so selection, lifecycle and audit commit once."""
        token = self.bound_records.set(rows)
        try:
            return callback()
        finally:
            self.bound_records.reset(token)

    @staticmethod
    def version(rows, version_id):
        record = rows.get('planning_version', version_id)
        if record is None:
            raise PlanningError('MISSING_REQUIRED_FIELDS', 'Baseline/proposal not found', 'repository')
        return record

    def get_version(self, version_id):
        with self.records() as rows:
            return self.version(rows, version_id)

    def selected(self, plan_id):
        with self.records() as rows:
            pointer = rows.get('planning_selected', plan_id)
            return pointer['versionId'] if pointer else None

    def accepted(self, proposal_id):
        with self.records() as rows:
            pointer = rows.get('planning_acceptance', proposal_id)
            return self.version(rows, pointer['versionId']) if pointer else None

    def lifecycle(self, plan_id):
        selected = self.selected(plan_id)
        return dict(planId=plan_id, selectedVersionId=selected, planStatus='PLANNED' if selected else 'DRAFT')

    def save_run(self, result, records, traces):
        validate('AgentResult', result)
        for record in records:
            validate('ItineraryVersion', record['version'])
        for event in traces:
            validate('TraceEvent', event)
        with self.records() as rows:
            # Cloud RPC uses compare-and-swap; immutable identifiers cannot be overwritten.
            identities = [('planning_run', result['runId'])] + [
                ('planning_version', r['version']['versionId']) for r in records]
            if len(identities) != len(set(identities)) or any(rows.get(*key) is not None for key in identities):
                raise PlanningError('PERSISTENCE_FAILED', 'Planning identifiers already exist', 'repository')
            rows.put('planning_run', result['runId'], result)
            for record in records:
                rows.put('planning_version', record['version']['versionId'], record)
            for event in traces:
                rows.trace(event)

    def adopt(self, proposal_id, expected_baseline, at):
        with self.records() as rows:
            if rows.get('planning_acceptance', proposal_id):
                return self.version(rows, proposal_id)
            record = self.version(rows, proposal_id)
            version = record['version']
            pointer = rows.get('planning_selected', version['planId'])
            if (pointer['versionId'] if pointer else None) != expected_baseline:
                raise PlanningError('STALE_EVIDENCE', 'Selected baseline changed; compare and accept again', 'adoption')
            rows.put('planning_acceptance', proposal_id, dict(versionId=proposal_id))
            rows.put('planning_selected', version['planId'], dict(versionId=proposal_id))
            event = dict(schemaVersion='1.0.0', caseId=version['caseId'], correlationId=version['correlationId'],
                         sourceReferences=deepcopy(version['sourceReferences']), validationResults=[], errors=[],
                         requiresApproval=False, eventId=uid('trace'), runId=None, timestamp=at, actor='planning',
                         eventType='CONFIRMATION', subject=dict(subjectType='ItineraryVersion', subjectId=proposal_id,
                         materialVersion=version['versionNo']), parentEventId=None, executionMode=record['executionMode'],
                         summary='Explicit proposal acceptance; Plan lifecycle PLANNED; no real booking',
                         result='SUCCESS', approvalId=None)
            rows.trace(event)
            return record

    def find_by_case(self, case_id):
        return [event for event in self.repository.find_by_case(case_id) if event['actor'] == 'planning']
