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


def connect_planning(operations, offers, reviewer, planning_repository, clock=None, planner=None, planner_factory=None):
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
        return PlanningRuntime(load_context=operations.load_context, offers=offers, access=operations.access,
                               entitlement=CaseEntitlements(operations, case_id), reviewer=reviewer,
                               repository=planning_repository, clock=clock or operations.clock,
                               execution_mode="FIXTURE", planner=planner_factory() if planner_factory else planner)
    class PlanningAdapter:
        def handle_case(self, case):
            return TravelPlanningAgent(runtime(case["caseId"])).handle_case(case)
    def adopt(actor, version_id, baseline, *, accepted=False):
        record = planning_repository.get_version(version_id)
        return accept_proposal(runtime(record["version"]["caseId"]), actor, version_id, baseline, accepted=accepted)
    operations.specialists["planning"] = PlanningAdapter()
    operations.adopt = adopt
    return operations
