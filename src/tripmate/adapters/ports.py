from typing import Protocol


class LLMService(Protocol):
    def extract(self, content: str, schema: dict) -> dict:
        ...

    def draft(self, context: dict) -> str:
        ...

    def explain(self, result: dict) -> str:
        ...


class ApprovedOfferLookup(Protocol):
    def find_selectable(self, criteria: dict, at: str) -> list:
        """Recheck APPROVED and expiry on read; preserve sources (B08)."""
        ...
