"""Common B01 calling convention; implementations replace the explicit stub."""
from datetime import datetime, timezone
from typing import Protocol
from uuid import uuid4

from tripmate.contracts import validate


class Agent(Protocol):
    agent_id: str
    owner: str

    def handle_case(self, case: dict) -> dict:
        """Accept a validated confirmed Case; return a validated AgentResult."""
        ...


class StubAgent:
    agent_id: str
    owner: str

    def handle_case(self, case: dict) -> dict:
        validate("Case", case)
        result = {
            "schemaVersion": "1.0.0",
            "caseId": case["caseId"],
            "correlationId": case["correlationId"],
            "sourceReferences": case["sourceReferences"],
            "validationResults": [{
                "ruleId": "AGENT_IMPLEMENTATION", "ruleVersion": "1.0.0",
                "outcome": "NOT_EVALUATED", "reason": "B01 module boundary only.",
                "checkedAt": datetime.now(timezone.utc).isoformat(), "sourceIds": [],
            }],
            "errors": [{
                "code": "NOT_IMPLEMENTED", "message": f"{self.agent_id} is a B01 stub.",
                "step": "handle_case", "retryable": False, "sourceIds": [],
            }],
            "requiresApproval": case["requiresApproval"],
            "runId": str(uuid4()), "agent": self.agent_id,
            "status": "FAILURE", "executionMode": "STUB",
            "findings": [], "proposedResponse": None, "subjects": [],
            "review": None, "approvalIds": [],
            "nextAction": f"Implement the module owned by {self.owner} before execution.",
        }
        validate("AgentResult", result)
        return result
