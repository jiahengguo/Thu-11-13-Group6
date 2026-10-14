"""Versioned travel-factor port and strict evidence checks; no invented external facts."""
from copy import deepcopy
from typing import Protocol

from .common import PlanningError, timestamp


class TravelFactorService(Protocol):
    def snapshot(self, request: dict, quotes: list, at: str) -> dict:
        """Return sources, weather, delays, routes, venues for the exact request.

        Each fact has capturedAt/validUntil/sourceIds. Coverage is checked separately
        from freshness. Adapters may combine weather, routing, traffic and venue APIs.
        """
        ...


class FixtureTravelFactors:
    """Explicit test adapter; callers can change data to test revalidation."""
    def __init__(self, data):
        self.data = deepcopy(data)

    def snapshot(self, request, quotes, at):
        return deepcopy(self.data)


def load_factors(provider, request, quotes, at, mode):
    if provider is None:
        raise PlanningError('TOOL_UNAVAILABLE', 'Daily planning requires a TravelFactorService', 'factors')
    data = deepcopy(provider.snapshot(deepcopy(request), deepcopy(quotes), at))
    if not isinstance(data, dict) or set(data) != {'sources', 'weather', 'delays', 'routes', 'venues'}:
        raise PlanningError('INVALID_CONTRACT', 'Invalid travel-factor snapshot', 'factors')
    if not all(isinstance(data[k], list) for k in data):
        raise PlanningError('INVALID_CONTRACT', 'Factor collections must be lists', 'factors')
    sources = {s['sourceId']: s for s in data['sources']}
    if len(sources) != len(data['sources']) or not sources:
        raise PlanningError('STALE_EVIDENCE', 'Missing or duplicate factor sources', 'factors')
    for source in sources.values():
        if (source['freshness'] != 'FRESH' or timestamp(source['capturedAt']) > timestamp(at)
                or (mode == 'REAL' and source['simulated'] is not False)):
            raise PlanningError('STALE_EVIDENCE', 'Stale or simulated factor evidence in REAL mode', 'factors')
    # Reject malformed/stale provider snapshots rather than silently ignore unknown risk.
    for group in ('weather', 'delays', 'routes', 'venues'):
        for fact in data[group]:
            if (not fact['sourceIds'] or any(s not in sources for s in fact['sourceIds'])
                    or not timestamp(fact['capturedAt']) <= timestamp(at) < timestamp(fact['validUntil'])):
                raise PlanningError('STALE_EVIDENCE', 'Factor evidence expired or unresolved: ' + group, 'factors')
    return data
