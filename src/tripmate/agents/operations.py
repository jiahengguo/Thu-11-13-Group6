"""Jiaheng: UC-05 intake/coordination/outbound communication; UC-07 membership."""
from .base import StubAgent


class OperationsAgent(StubAgent):
    agent_id = "operations"
    owner = "Jiaheng"

    def __init__(self, service=None):
        self.service = service

    def handle_case(self, case):
        if self.service is None:
            return super().handle_case(case)
        from tripmate.contracts import validate
        from tripmate.operations.common import envelope, identifier
        validate("Case", case)
        rec = self.service.repository.read("case", case["caseId"])
        if not rec or rec["case"] != case:
            from tripmate.operations.common import OperationsError
            raise OperationsError("UNCONFIRMED_REQUEST", "Only the current persisted case may be dispatched.")
        view = self.service.dispatch(case["requesterId"], "agent:" + str(rec["revision"]), case["caseId"], rec["revision"])
        current = view["case"]
        result = envelope(current["caseId"], current["correlationId"], current["sourceReferences"])
        result.update(runId=identifier(), agent="operations", executionMode="FIXTURE",
                      status="HUMAN_ASSISTANCE" if current["status"] == "HUMAN_ASSISTANCE" else "SUCCESS",
                      findings=["Operations case state: " + current["status"]], proposedResponse=None,
                      subjects=[{"subjectType": "Case", "subjectId": current["caseId"], "materialVersion": view["revision"]}],
                      review=None, approvalIds=[], nextAction="Use the controlled Operations case view and explicit delivery action.")
        result["validationResults"] = current["validationResults"]
        result["requiresApproval"] = current["requiresApproval"]
        if current["errors"] and result["status"] != "HUMAN_ASSISTANCE":
            result.update(status="FAILURE", errors=current["errors"])
        validate("AgentResult", result)
        return result
