from typing import Protocol


class TraceRepository(Protocol):
    def append(self, event: dict) -> None:
        """Validate TraceEvent; raise on save failure rather than reporting success."""
        ...

    def find_by_case(self, case_id: str) -> list:
        ...


class ApprovalRepository(Protocol):
    def save(self, approval: dict) -> None:
        """Append a version-scoped decision; never overwrite approval history."""
        ...

    def find_by_subject(self, subject: dict) -> list:
        ...
