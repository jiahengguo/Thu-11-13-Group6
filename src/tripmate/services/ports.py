"""Report G-04 service boundaries; implementations belong to later cards."""
from typing import Protocol


class EntitlementService(Protocol):
    def evaluate(self, traveller_id: str, action: str, dates: dict) -> dict:
        """Return ALLOWED, DENIED or VERIFICATION_FAILED with evidence (B07)."""
        ...


class ConstraintValidationService(Protocol):
    def validate_plan(self, version: dict) -> list:
        """Return structured rule results; LLM output cannot override them (B04)."""
        ...

    def validate_proposal(self, subject: dict) -> list:
        ...


class PricingService(Protocol):
    def calculate(self, offer: dict, discount: dict) -> dict:
        """Return a PriceBreakdown on the same AUD quoted-quantity basis (B04)."""
        ...


class ReviewService(Protocol):
    def review(self, subject: dict, evidence: list, policies: list) -> dict:
        """Return a version-scoped ReviewResult (B10)."""
        ...


class AccessControlService(Protocol):
    def authorise(self, requester_id: str, action: str, subject: dict) -> bool:
        """Identity/ownership decisions run on the backend (B06/B07)."""
        ...
