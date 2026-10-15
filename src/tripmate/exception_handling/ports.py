"""Injected dependencies; mocks are explicit, never labelled real integrations."""
from copy import deepcopy
from typing import Protocol
from uuid import uuid4
from datetime import datetime, timezone

class ContextSource(Protocol):
    def load(self, case_id: str) -> dict: ...

class SupplierPort(Protocol):
    def alternatives(self, context: dict) -> list: ...

class PlanningPort(Protocol):
    def revise(self, context: dict, offer: dict) -> list: ...

class MemoryContext:
    def __init__(self, contexts):
        self.contexts = deepcopy(contexts)

    def load(self, case_id):
        return deepcopy(self.contexts[case_id])

class SimulatedSupplier:
    def alternatives(self, context):
        return deepcopy(context["supplierOffers"])

class SimulatedPlanning:
    def revise(self, context, offer):
        # Explicit fixture scope: replace one cancelled first flight, preserve all other items.
        return [deepcopy(offer["replacement"] if item["itemId"] == context["issue"]["itemId"] else item)
                for item in context["itinerary"]["items"]]

class SimulatedReviewer:
    def review(self, subject, evidence, policies):
        reasons = []
        if not subject["checks"] or any(c["outcome"] != "PASS" for c in subject["checks"]):
            reasons.append("Required deterministic checks have not all passed.")
        ids = {e["sourceId"] for e in evidence}
        if not subject["sourceIds"] or not set(subject["sourceIds"]).issubset(ids):
            reasons.append("Unresolved evidence references.")
        if subject["subject"]["subjectType"] == "ResolutionRecommendation" and not policies:
            reasons.append("No applicable simulated policy.")
        return {"reviewId": str(uuid4()), "subject": subject["subject"],
                "outcome": "REVISION_REQUIRED" if reasons else "PASS", "reasons": reasons,
                "reviewedAt": datetime.now(timezone.utc).isoformat(),
                "policyVersion": "SIMULATED_EXCEPTION_REVIEW_1",
                "sourceIds": subject["sourceIds"]}
