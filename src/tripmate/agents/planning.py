"""Moore: UC-01 complete planning/comparison; UC-02 confirmed revisions."""
from .base import StubAgent


class TravelPlanningAgent(StubAgent):
    agent_id = "planning"
    owner = "Moore"

    def __init__(self, runtime=None):
        self.runtime = runtime

    def handle_case(self, case):
        if self.runtime is None:
            # The team composition root still has no B02/B07/B08/B10 adapters.
            return super().handle_case(case)
        from tripmate.planning.application import run_case
        return run_case(self.runtime, case)
