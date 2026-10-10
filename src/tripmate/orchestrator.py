"""Composition root for one process. No direct external specialist endpoints."""
from tripmate.agents.operations import OperationsAgent
from tripmate.agents.planning import TravelPlanningAgent
from tripmate.agents.exception import CustomerExceptionAgent
from tripmate.agents.supplier import SupplierPartnershipAgent


def build_agents() -> dict:
    agents = (
        OperationsAgent(), TravelPlanningAgent(),
        CustomerExceptionAgent(), SupplierPartnershipAgent(),
    )
    return {agent.agent_id: agent for agent in agents}
