# UC-07 adopted itinerary maps

Travellers open **My trips → Open itinerary map**. The authenticated endpoint
`POST /api/operations/premium` accepts `requestKey`, `action: ROUTE_MAP`, and
`versionId`. It verifies ownership, release review, current adoption and fresh
Paid membership. Expired membership cannot replay previously granted map data.
The membership panel's existing sample map remains explicitly a demo.

`BenefitsProvider.route_for_version(version)` is the replacement port for a
future map provider. The default implementation uses actual adopted itinerary
items and timestamps but deterministic schematic coordinates. It returns
`routePoints` (label, at, itemId, kind, x, y), mapHeight, planId, versionId,
mapNotice, source and simulationOnly. A real provider must map verified place
identifiers to geographic coordinates and supply its own truthful source and
simulation notice. Provider failures propagate; no unrelated demo route is
substituted for a requested itinerary.

## Verification

Run with PYTHONPATH=src:

    python -m unittest discover -s tests -p test_trip_map.py
    python -m unittest discover -s tests -p test_uc07_benefits.py
    python -m unittest discover -s tests -p test_operations.py

The HTTP tests cover itinerary-derived points, cross-user and role access,
expired membership replay, unreleased/unadopted versions and provider failures.
These use isolated authenticated cloud fixtures, not the supplied live accounts.

Live verification on 2026-11-01 used the supplied stage2-demo accounts and
local ignored configuration. Supabase private storage was reachable; all four
accounts authenticated and returned the expected roles. Free route-map access
was DENIED; Paid access was ALLOWED. The existing ACTIVE itinerary of the Paid
account returned six schematic points through the new adopted-version service
path. This exercised the real Supabase repository, current profile, release
checks and current adoption. Only normal premium audit records were written;
no itinerary, account or membership was changed.

This live check called the service directly after verifying Supabase identities;
it does not establish browser end-to-end acceptance. The authenticated HTTP
boundary is covered by the isolated tests above. Browser rendering and real
geographic navigation remain unverified; live routing and external traffic are
not implemented by the schematic provider. Never commit passwords or keys.
