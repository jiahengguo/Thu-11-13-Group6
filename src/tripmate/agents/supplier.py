"""Jason: UC-06 offer/pricing assessment; UC-08 campaign proposals."""
from .base import StubAgent


class SupplierPartnershipAgent(StubAgent):
    agent_id = "supplier"
    owner = "Jason"

    def __init__(self, runtime=None):
        self.runtime = runtime

    def handle_case(self, case):
        if self.runtime is None:
            return super().handle_case(case)
        return self.runtime.handle_case(case)
