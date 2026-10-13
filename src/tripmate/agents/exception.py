"""wrd: UC-03 recovery; UC-04 evidence-supported complaint recommendations."""
from .base import StubAgent

class CustomerExceptionAgent(StubAgent):
    agent_id = 'exception'
    owner = 'wrd'

    def __init__(self, runtime=None):
        self.runtime = runtime

    def handle_case(self, case):
        # Unconfigured composition roots retain the explicit fail-closed stub.
        if self.runtime is None:
            return super().handle_case(case)
        return self.runtime.handle_case(case)
