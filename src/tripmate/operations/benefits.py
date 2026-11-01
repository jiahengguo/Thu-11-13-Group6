"""Replaceable UC-07 content port. It never grants membership or approves offers."""
from typing import Protocol

class BenefitsProvider(Protocol):
    def route(self): ...
    def route_for_version(self, version): ...
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


    def route_for_version(self, version):
        # Deterministic schematic positions, not invented geographic coordinates.
        points = []
        legs = sorted(version['items'], key=lambda item: item['startAt'])
        for item in legs:
            for name, at in ((item['origin'], item['startAt']), (item['destination'], item['endAt'])):
                points.append({'label': name, 'at': at, 'itemId': item['itemId'],
                               'kind': item['productType'], 'x': 40 + (len(points) % 5) * 80,
                               'y': 40 + (len(points) // 5) * 70})
        return {'routePoints': points, 'mapHeight': max(220, 100 + ((len(points)-1)//5)*70),
                'planId': version['planId'], 'versionId': version['versionId'],
                'mapNotice': 'Your adopted itinerary: simulated schematic positions; not geographic navigation.',
                'source': 'adopted-itinerary-schematic-v1', 'simulationOnly': True}
