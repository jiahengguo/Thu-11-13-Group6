"""Replaceable UC-07 content port. It never grants membership or approves offers."""
from typing import Protocol

class BenefitsProvider(Protocol):
    def route(self): ...
    def advertisements(self): ...
    def offers(self): ...

class SimulatedBenefits:
    """Explicit sample inputs; replace this provider when verified sources exist."""
    def route(self):
        return {"routePoints": [{"label": "Sydney Central", "x": 90, "y": 60},
                                {"label": "Melbourne Centre", "x": 300, "y": 160}],
                "mapNotice": "Simulated Sydney–Melbourne sample route; not your booked itinerary or live navigation.",
                "source": "uc07-demo-route-v1", "simulationOnly": True}

    def advertisements(self):
        return [{"label": "Advertisement · simulated", "text": "Explore the sample Australian travel collection.",
                 "source": "uc07-demo-ad-v1"}]

    def offers(self):
        return [{"id": "demo-paid-benefit-v1", "title": "Sample Paid member benefit", "approved": True,
                 "eligibleTiers": ["PAID"], "validFrom": "2026-01-01T00:00:00Z",
                 "validUntil": "2030-01-01T00:00:00Z", "simulationOnly": True,
                 "source": "Simulated UC-08 approved-rule input", "version": 1}]

