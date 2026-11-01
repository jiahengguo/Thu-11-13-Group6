"""Explicit Planning handoff; import only after the separate Planning PR is merged.

No Supplier or Reviewer implementation is replaced by fabricated passing output.
"""
from copy import deepcopy
from .common import OperationsError


class CaseEntitlements:
    """The shared three-argument port lacks planId; bind it to a confirmed case.

Revisions and adoptions of the same plan must not consume an extra Free trip slot.
"""
    def __init__(self, operations, case_id):
        self.operations, self.case_id = operations, case_id

    def evaluate(self, traveller_id, action, dates):
        rec = self.operations.repository.read("case", self.case_id)
        if not rec or rec["case"]["requesterId"] != traveller_id or rec.get("context", {}).get("request", {}).get("travelDates") != dates:
            return {"travellerId": traveller_id, "action": action, "outcome": "VERIFICATION_FAILED", "reason": "Entitlement context does not match the confirmed request."}
        facts = deepcopy(dates)
        baseline = rec["context"]["request"]["baselineVersionId"]
        if baseline:
            facts["planId"] = self.operations.planning_repository.get_version(baseline)["version"]["planId"]
        elif rec.get("planId"):
            facts["planId"] = rec["planId"]
        return self.operations.entitlement.evaluate(traveller_id, action, facts)


def connect_planning(operations, offers, reviewer, planning_repository, clock=None, planner=None, planner_factory=None, factors=None):
    """Connect installed Planning with the real Operations services on simulated data.

Offers and Reviewer MUST be supplied by their owners. Test substitutes stay FIXTURE.
Each case gets its own scoped entitlement adapter. Shared DB is supported.
"""
    try:
        from tripmate.agents.planning import TravelPlanningAgent
        from tripmate.planning.application import PlanningRuntime, accept_proposal
    except ImportError as exc:
        raise OperationsError("TOOL_UNAVAILABLE", "Merge the Travel Planning module before connecting it.") from exc
    if planner is not None and planner_factory is not None:
        raise ValueError('Provide planner or planner_factory, not both')
    operations.planning_repository = planning_repository
    def runtime(case_id):
        expected = operations.repository.read('case', case_id)
        def phase(state, run_id):
            from uuid import uuid4
            if state not in {'FEASIBLE', 'UNDER_REVIEW'}:
                raise OperationsError('INVALID_CONTRACT', 'Unknown Planning progress state.')
            with operations.repository.transaction() as rows:
                rec = rows.get('case', case_id)
                if (not rec or rec['case']['status'] != 'IN_PROGRESS' or rec['revision'] != expected['revision']
                        or rec.get('runId') != expected.get('runId') or rec['case']['confirmedRequest'] != expected['case']['confirmedRequest']):
                    raise OperationsError('STALE_EVIDENCE', 'Planning invocation is no longer current.')
                previous = rows.get('planning_assessment', case_id)
                value = dict(caseId=case_id, state=state, runId=run_id, subjects=[],
                             caseRevision=rec['revision'], responseVersion=rec['responseVersion'], updatedAt=operations.clock())
                rows.put('planning_assessment_event', str(uuid4()), dict(value, previousState=previous['state'] if previous else None))
                rows.put('planning_assessment', case_id, value)
        return PlanningRuntime(load_context=operations.load_context, offers=offers, access=operations.access,
                               entitlement=CaseEntitlements(operations, case_id), reviewer=reviewer,
                               repository=planning_repository, clock=clock or operations.clock,
                               execution_mode="FIXTURE", phase=phase, planner=planner_factory() if planner_factory else planner, factors=factors)
    class PlanningAdapter:
        def handle_case(self, case):
            return TravelPlanningAgent(runtime(case["caseId"])).handle_case(case)
    def adopt(actor, version_id, baseline, *, accepted=False):
        record = planning_repository.get_version(version_id)
        return accept_proposal(runtime(record["version"]["caseId"]), actor, version_id, baseline, accepted=accepted)
    operations.specialists["planning"] = PlanningAdapter()
    def validate_release(record):
        from tripmate.planning.application import validate_saved_proposal
        from tripmate.planning.common import PlanningError
        try:
            validate_saved_proposal(runtime(record['version']['caseId']), record)
        except PlanningError as exc:
            raise OperationsError(exc.code, str(exc)) from exc
    operations.validate_planning_release = validate_release
    operations.adopt = adopt
    return operations
