# UC-04 complaint investigation in the authenticated portal

## Change

The default portal previously rejected every complaint context. Operators can now record simulated service evidence, category (DELAY, ITINERARY, SUPPLIER_TERMS), observed arrival and an explicit policy source/action. Evidence binds to the confirmed request and selected immutable itinerary version. Only authorised Operators can write it; the traveller report is not treated as verified supplier evidence.

Delay investigation reconciles scheduled and observed arrivals, records deterministic delay minutes, verifies policy assertions and invokes the shared reviewer. EXPLAIN_AND_APOLOGISE returns a recommendation for Operations review and delivery. HUMAN_REVIEW_REFUND requires a separate human proposal decision; the restricted flag also preserves compensation approval requirements. No refund or compensation is executed.

Itinerary and supplier-terms complaints collect ProjectComplaintFindings and refer to human handling when no applicable automated resolution policy exists. Missing evidence requests clarification; low confidence, legal/safety concerns and unavailable dependencies retain the existing escalation rules. A referral does not mean the complaint has been resolved.

## Demonstration

1. Traveller confirms a complaint referencing an adopted itinerary.
2. Operator opens the complaint and records the affected service, evidence source, future evidence expiry, confidence and concerns. For a delay, enter a past observed arrival after the itinerary's scheduled arrival.
3. Choose the complaint category and supplied simulated policy action/source. Confirm the evidence explicitly.
4. Traveller starts processing, or re-confirms if earlier evidence was replaced.
5. Operator inspects findings and review. For a restricted proposal, record the separate scoped approval before response review and Operations delivery.
6. Inspect the case history. Evidence replacement invalidates previous proposal authority; changed selected itinerary/evidence fails the pre-delivery freshness check.

## Requirement mapping and validation

- AC-UC04-01: existing confirmed complaint intake plus context bound to owner/request/selected version.
- AC-UC04-02/03: recorded service/policy sources, deterministic delay and shared reviewer; authenticated delay-to-delivery test.
- AC-UC04-04: missing evidence clarification, low-confidence referral, specialist findings for itinerary complaints; existing exception conflict/failure regressions.
- AC-UC04-05: refund proposal remains AWAITING_HUMAN_APPROVAL and hidden from traveller until decisions/review/delivery.
- Traceability: existing shared Exception import and Operations evidence/decision events; immutable baseline preserved.

Validation: 50 Exception regression tests and 6 complaint portal tests passed; JavaScript syntax and diff whitespace checks passed. Tests use isolated cloud/provider doubles and the real HTTP portal. Real-cloud/browser visual acceptance and release-ZIP acceptance were not run.

## Data boundary

Operator inputs are explicitly simulated records and policy evidence, not production policy verification. Replace the PortalExceptionContexts input adapter with a verified service/policy provider when available, preserving source IDs, versions, timestamps, request ownership and evidence-change invalidation. Automated delay policy supports explanation/apology or refund review; other categories deliberately use documented human referral, as permitted by UC-04. No real legal policy or automatic compensation amount is inferred.
