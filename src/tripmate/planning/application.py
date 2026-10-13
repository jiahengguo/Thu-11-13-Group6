"""Planning application boundary with injected Operations/Supplier/Reviewer services."""
from copy import deepcopy
from dataclasses import dataclass
from typing import Callable

from tripmate.contracts import validate
from .common import PlanningError, envelope, now, subject, timestamp, uid
from .engine import PlanningEngine
from .validation import PlanningValidator, validate_product


@dataclass
class PlanningRuntime:
    # load_context(caseId) -> {request: TravelRequest, spec: PlanningSpec}.
    load_context: Callable
    offers: object  # ApprovedOfferLookup returning documented offer/price/product bundles.
    access: object  # AccessControlService, fails closed.
    entitlement: object  # EntitlementService; fresh evaluate at create/revise/present/adopt.
    reviewer: object  # ReviewService, returns v1 ReviewResult.
    repository: object  # PlanningRepository; atomic versions/result/trace transaction.
    clock: Callable = now
    execution_mode: str = "FIXTURE"
    llm: object = None  # Optional shared LLMService.explain; advisory text is never a gate.
    planner: object = None  # Optional model proposal loop, still subject to deterministic checks.

    def __post_init__(self):
        if self.execution_mode not in {"FIXTURE", "REAL"}:
            raise ValueError("Explicit FIXTURE or REAL execution mode required")


def require_entitlement(runtime, request, action):
    decision = runtime.entitlement.evaluate(request["travellerId"], action, deepcopy(request["travelDates"]))
    if (decision.get("outcome") != "ALLOWED" or decision.get("travellerId") != request["travellerId"]
            or decision.get("action") != action):
        raise PlanningError("ENTITLEMENT_DENIED", "Membership service did not allow " + action, "entitlement")


def trace(result, event_type, summary, at, ref=None, parent=None):
    event = envelope(result)
    event.update(eventId=uid("trace"), runId=result["runId"], timestamp=at, actor="planning",
                 eventType=event_type, subject=ref or {"subjectType": "Case", "subjectId": result["caseId"], "materialVersion": 1},
                 parentEventId=parent, executionMode=result["executionMode"], summary=summary,
                 result="FAILURE" if result["status"] == "FAILURE" else "SUCCESS", approvalId=None)
    event["validationResults"] = deepcopy(result["validationResults"])
    event["errors"] = deepcopy(result["errors"])
    return event


def lookup(runtime, request):
    quotes = deepcopy(runtime.offers.find_selectable(deepcopy(request), runtime.clock()))
    for q in quotes:
        if set(q) != {"offer", "price", "product"}:
            raise PlanningError("INVALID_CONTRACT", "Supplier adapter must return offer/price/product bundles", "lookup")
        validate("SupplierOffer", q["offer"])
        validate("PriceBreakdown", q["price"])
        validate_product(q["product"])
    if runtime.execution_mode == "REAL" and any(s["simulated"] for q in quotes for s in q["offer"]["sourceReferences"]):
        raise PlanningError("INVALID_CONTRACT", "Simulated data cannot be labelled REAL", "lookup")
    return quotes


def run_case(runtime, case):
    validate("Case", case)
    result = envelope(case)
    result.update(runId=uid("run"), agent="planning", status="FAILURE", executionMode=runtime.execution_mode,
                  findings=[], proposedResponse=None, subjects=[], review=None, approvalIds=[],
                  nextAction="Operations must inspect the recorded outcome.")
    records, events = [], []
    step = "context"
    try:
        if (case["caseKind"] != "CUSTOMER" or case["caseType"] not in {"TRAVEL_PLANNING", "PLAN_REVISION"}
                or case["status"] not in {"CONFIRMED", "ASSIGNED", "IN_PROGRESS"}):
            raise PlanningError("INVALID_CONTRACT", "Case is not an active confirmed planning/revision case")
        if case["unresolvedQuestions"] or case["errors"]:
            raise PlanningError("UNCONFIRMED_REQUEST", "Resolve outstanding request questions first")
        if case["requiresApproval"] or case["humanRequestCount"] >= 2:
            raise PlanningError("HUMAN_ASSISTANCE_REQUIRED", "Operations must handle requested human review before planning")
        context = deepcopy(runtime.load_context(case["caseId"]))
        request, spec = context["request"], context["spec"]
        validate("TravelRequest", request)
        if runtime.execution_mode == "REAL" and any(s["simulated"] for s in case["sourceReferences"] + request["sourceReferences"]):
            raise PlanningError("INVALID_CONTRACT", "Simulated request must remain labelled FIXTURE")
        if (request["caseId"] != case["caseId"] or request["correlationId"] != case["correlationId"]
                or request["travellerId"] != case["requesterId"]):
            raise PlanningError("ACCESS_DENIED", "Case and request ownership/context do not match")
        if request["requiresApproval"]:
            raise PlanningError("APPROVAL_REQUIRED", "Restricted request must pass shared approval handling")
        is_revision = case["caseType"] == "PLAN_REVISION"
        if is_revision != bool(request["baselineVersionId"]):
            raise PlanningError("INVALID_CONTRACT", "Revision case and baseline reference must agree")
        step = "access"
        action = "REVISE_PLAN" if is_revision else "CREATE_PLAN"
        if not runtime.access.authorise(case["requesterId"], action, deepcopy(request)):
            raise PlanningError("ACCESS_DENIED", "Operations access service denied planning")
        step = "entitlement"
        require_entitlement(runtime, request, action)
        baseline = None
        if is_revision:
            baseline = runtime.repository.get_version(request["baselineVersionId"])
            if baseline["version"]["travellerId"] != request["travellerId"]:
                raise PlanningError("ACCESS_DENIED", "Baseline belongs to another traveller", "revision")
            if not runtime.access.authorise(case["requesterId"], "READ_PLAN", deepcopy(baseline["version"])):
                raise PlanningError("ACCESS_DENIED", "Baseline access denied", "revision")
        step = "lookup"
        quotes = lookup(runtime, request)
        sources = {s["sourceId"]: deepcopy(s) for s in case["sourceReferences"]}
        for s in request["sourceReferences"] + [s for q in quotes for group in [q["offer"], q["price"]] for s in group["sourceReferences"]]:
            if s["sourceId"] in sources and sources[s["sourceId"]] != s:
                raise PlanningError("STALE_EVIDENCE", "Conflicting evidence identifiers", "lookup")
            sources[s["sourceId"]] = deepcopy(s)
        result["sourceReferences"] = list(sources.values())
        step = "generation"
        records, excluded = (runtime.planner or PlanningEngine(runtime.clock)).generate(request, quotes, spec, baseline)
        result["findings"] = [f"Evaluated {len(records) + len(excluded)} combinations from the supplied inventory."]
        for exclusion in excluded:
            result["findings"].append("Excluded " + ", ".join(exclusion["offerIds"]) + ": "
                                      + "; ".join(r["ruleId"] + " — " + r["reason"] for r in exclusion["checks"]))
        if not records:
            result["validationResults"] = [r for e in excluded for r in e["checks"]]
            raise PlanningError("NO_FEASIBLE_ITINERARY", "No complete candidate passes within the supplied inventory; constraints unchanged", "validation")
        result["validationResults"] = deepcopy(records[0]["version"]["validationResults"])
        for record in records:
            step = "review"
            version = record["version"]
            reviewed = runtime.reviewer.review(deepcopy(version), deepcopy(version["sourceReferences"]),
                                               ["planning-1.0", record["ranking"]["configVersion"]])
            if reviewed.get("subject") != subject(version) or reviewed.get("outcome") != "PASS":
                raise PlanningError("REVIEW_FAILED", "Shared Reviewer did not pass this exact proposal version", "review")
            if timestamp(reviewed["reviewedAt"]) > timestamp(runtime.clock()):
                raise PlanningError("REVIEW_FAILED", "Review timestamp is invalid", "review")
            version["review"], version["assessmentState"] = reviewed, "REVIEWED"
            validate("ItineraryVersion", version)
            record["executionMode"] = runtime.execution_mode
        step = "entitlement"
        require_entitlement(runtime, request, "PRESENT_PLAN")
        best = records[0]
        result.update(status="SUCCESS", subjects=[subject(r["version"]) for r in records],
                      review=deepcopy(best["version"]["review"]),
                      proposedResponse=f"{len(records)} validated option(s). Recommended {best['version']['versionId']}: "
                      + best["version"]["tradeOffs"][0] + (" No eligible alternative was found." if len(records) == 1 else "")
                      + " Proposal only; not a booking or an adopted itinerary.",
                      nextAction="Operations rechecks release permissions and presents the version IDs; adoption needs separate explicit acceptance.")
        if runtime.llm is not None:
            step = "llm"
            try:
                # Optional drafting; deterministic facts remain the authoritative proposed response.
                advice = runtime.llm.explain(deepcopy({"mode": request["rankingMode"], "options": [r["metrics"] for r in records]}))
                if not isinstance(advice, str) or not advice.strip():
                    raise ValueError("Empty explanation")
                best["llmDraftForReview"] = advice
                result["findings"].append("An optional LLM draft is stored separately for review; it is not the released response.")
            except Exception:
                result["findings"].append("Optional LLM explanation unavailable; deterministic comparisons retained.")
        previous = None
        for record in records:
            for kind, text in [("VALIDATION", "Complete hard constraints checked"),
                               ("REVIEW", "Exact proposal reviewed"), ("VERSION_CREATED", "Immutable proposal saved")]:
                event = trace(result, kind, text, runtime.clock(), subject(record["version"]), previous)
                event["validationResults"] = deepcopy(record["version"]["validationResults"])
                events.append(event)
                previous = event["eventId"]
    except Exception as exc:
        code = exc.code if isinstance(exc, PlanningError) else "INVALID_CONTRACT" if isinstance(exc, (ValueError, KeyError, TypeError)) else "TOOL_UNAVAILABLE"
        result.update(status="FAILURE", proposedResponse=None, subjects=[], review=None,
                      errors=[{"code": code, "message": str(exc) if isinstance(exc, PlanningError) else "Planning dependency or input failed; inspect the integration boundary.",
                               "step": exc.step if isinstance(exc, PlanningError) else step, "retryable": code in {"TOOL_UNAVAILABLE", "PERSISTENCE_FAILED"}, "sourceIds": []}])
        records = []
        events = [trace(result, "FAILURE", result["errors"][0]["message"], runtime.clock())]
    try:
        runtime.repository.save_run(result, records, events)
    except Exception:
        result.update(status="FAILURE", proposedResponse=None, subjects=[], review=None,
                      errors=[{"code": "PERSISTENCE_FAILED", "message": "Planning outcome was not saved; no result released.",
                               "step": "persistence", "retryable": True, "sourceIds": []}])
    validate("AgentResult", result)
    return result


def accept_proposal(runtime, traveller_id, proposal_id, expected_baseline, *, accepted=False):
    """Explicit customer acceptance, separate from confirmed requirement changes."""
    if accepted is not True:
        raise PlanningError("UNCONFIRMED_REQUEST", "Explicit acceptance of the exact proposal is required", "adoption")
    record = runtime.repository.get_version(proposal_id)
    version, request = record["version"], record["request"]
    if version["travellerId"] != traveller_id or not runtime.access.authorise(traveller_id, "ADOPT_PLAN", deepcopy(version)):
        raise PlanningError("ACCESS_DENIED", "Proposal access denied", "adoption")
    existing = runtime.repository.accepted(proposal_id)
    if existing:
        return existing  # Read-back, not a second adoption, even if membership later changes.
    if version["baselineVersionId"] != expected_baseline:
        raise PlanningError("STALE_EVIDENCE", "Acceptance references a different baseline", "adoption")
    require_entitlement(runtime, request, "ADOPT_PLAN")
    quotes = lookup(runtime, request)
    current = {q["offer"]["offerId"]: q for q in quotes}
    if any(current.get(q["offer"]["offerId"]) != q for q in record["quotes"]):
        raise PlanningError("STALE_EVIDENCE", "Supplier snapshot changed; regenerate comparison and obtain fresh acceptance", "adoption")
    checks = PlanningValidator(request, quotes, record["spec"], runtime.clock).validate_plan(version)
    if any(r["outcome"] != "PASS" for r in checks):
        raise PlanningError("NO_FEASIBLE_ITINERARY", "Proposal failed final validity checks", "adoption")
    review = runtime.reviewer.review(deepcopy(version), deepcopy(version["sourceReferences"]), ["planning-1.0"])
    if review.get("outcome") != "PASS" or review.get("subject") != subject(version) or version["requiresApproval"]:
        raise PlanningError("REVIEW_FAILED", "Current scoped review/approval is required", "adoption")
    checked_version = deepcopy(version)
    checked_version["review"] = review
    validate("ItineraryVersion", checked_version)
    if timestamp(review["reviewedAt"]) > timestamp(runtime.clock()):
        raise PlanningError("REVIEW_FAILED", "Future-dated review cannot authorise adoption", "adoption")
    try:
        return runtime.repository.adopt(proposal_id, expected_baseline, runtime.clock())
    except PlanningError:
        raise
    except Exception as exc:
        raise PlanningError("PERSISTENCE_FAILED", "Adoption was not saved; selected version is unchanged", "adoption") from exc
