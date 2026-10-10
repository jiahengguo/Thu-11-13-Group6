# TripMate AI shared contracts v1.0.0

Status: **implemented proposal, pending four-member approval**. Date: 10 October
2026 (Australia/Sydney). B01 owner: Jiaheng; reviewer: wrd. This document and the
schema bundle are versioned together. No member approval is inferred from tests.

## Authority and naming

Primary design baseline: `docs/TripMate_AI_stage1_report.pdf`, sections 2–7 and
G-04/G-05 (pages 30–31, enlarged G-04 on page 47). The current model companion is
`docs/diagrams/Elementary_Structure/G-04_Current_Model.md`. The older class
inventory explicitly identifies itself as historical and is not the implementation
baseline. The report's UC-05 creates an ExternalRequest before confirmation and
CustomerCase/SupplierCase afterwards; the historical timing conflict is resolved
in the report, not reproduced in this contract.

The machine-readable source of truth is
`src/tripmate/contracts/v1/schemas.json` (JSON Schema Draft 2020-12).
Select a public schema via `#/$defs/Case`, etc. Python consumers call
`tripmate.contracts.validate(name, payload)`; other languages can use the same
bundle with a Draft 2020-12 validator and enabled date/date-time format checks.
Unknown fields are rejected. Required nullable fields must be present as `null`.

B01 implementation names map to the report as follows:

| Wire name | Report model | Treatment |
| --- | --- | --- |
| Case | Case / CustomerCase / SupplierCase | Discriminated by caseKind; no Draft Case |
| Approval | HumanApproval | PENDING represents a request; DECIDED represents a recorded human decision |
| TraceEvent | TraceEntry within AgentRun | runId links an event to an execution; nullable for intake/operator events |
| AgentResult | AgentResult returned by Agent.handleCase | Explicit transport envelope for shared integration |
| ItineraryVersion.assessmentState | SM-02 assessment states | Separate from TravelPlan lifecycle used by membership rules |

## Shared envelope and primitive types

Every public contract requires schemaVersion, caseId, correlationId,
sourceReferences, validationResults, errors and requiresApproval. Correlation ID
is retained through handoffs, review, approval and response. Independent split
cases share correlationId and retain relatedCaseIds. Case IDs are nonempty on
Case, TravelRequest and ItineraryVersion. SupplierOffer, PriceBreakdown,
AgentResult, Approval and TraceEvent allow explicit `caseId: null` for the report's
case-independent campaign/operator work; do not invent a CustomerCase for UC-08.

- sourceReferences contains at least one Evidence-compatible source record:
  sourceId, sourceType, sourceReference, capturedAt, freshness, simulated.
  `sourceReference` may be a fixture URI, document locator or tool result ID;
  a citation is evidence provenance, not proof of correctness.
- ValidationResult: ruleId, ruleVersion, outcome (PASS/FAIL/UNSUPPORTED/
  NOT_EVALUATED), reason, checkedAt, sourceIds. Empty validationResults means
  **no checks recorded**, never an implicit pass.
- Error: code, message, step, retryable, sourceIds. Errors are safe summaries;
  do not include credentials, raw provider requests or private source content.
- Money: `{ "amount": "198.00", "currency": "AUD" }`. Amount is a decimal
  string, not a binary float. Use Decimal in future pricing implementations.
  Negative values are representable for margin/delta; domain rules determine
  where they are permitted. Markup rate is a decimal string ("0.10" means 10%).
- Dates: ISO calendar dates; timestamps: RFC 3339 with an explicit UTC offset.
  Use Australia/Sydney calendar boundaries for trip duration.
- SubjectRef: subjectType, subjectId, materialVersion. Reviews and approvals
  refer to the exact material version; matching an ID alone is insufficient.

## Eight public schemas

All listed fields are required; nullable fields are explicitly marked below.
The schema bundle supplies the complete nested field definitions and enums.

| Contract | Fields in addition to the shared envelope | Key rule / owner |
| --- | --- | --- |
| Case | caseKind, caseType, externalRequestId, requesterId, requesterType, confirmedAt, createdAt, status, coordinator, primaryHandler (nullable), relatedCaseIds, humanRequestCount, confirmedRequest, unresolvedQuestions, entitlementDecision (nullable) | Operations owns coordination; CustomerCase is Traveller-originated, SupplierCase supplier-originated |
| TravelRequest | requestId, travellerId, origin, destination, partySize, budgetCeiling, travelDates, rankingMode, confirmedAt, constraintSetId, constraintSetVersion, hardConstraints, preferences, baselineVersionId (nullable), confirmedChangedFields | Planning receives a confirmed constraint snapshot; revision retains baseline |
| SupplierOffer | offerId, materialVersion, supplierId, productId, productType, availableQuantity, quotedQuantity, unitBasis, supplierCost, mandatoryChargesIncluded, validFrom, validUntil, cancellationTerms, commercialTerms, status, priceBreakdownId (nullable), review (nullable), approvalId (nullable) | Supplier owns assessment; source cost remains unchanged |
| PriceBreakdown | priceBreakdownId, offerId, offerVersion, supplierCost, markupRate, basePrice, discountAmount, sellingPrice, marginAmount, minimumMargin, quotedQuantity, unitBasis, pricingConfigVersion, calculatedAt, memberOfferRuleId (nullable), entitlementDecisionId (nullable) | Immutable base/member quotation; same AUD and quantity basis |
| ItineraryVersion | planId, travellerId, versionId, versionNo, baselineVersionId (nullable), createdAt, assessmentState, planStatus, rankingMode, requestId, constraintSetId, constraintSetVersion, travelDates, items, totalPrice, assumptions, tradeOffs, exclusionReasons, review (nullable), approvalId (nullable) | Planning creates new immutable versions; no baseline overwrite |
| AgentResult | runId, agent, status, executionMode, findings, proposedResponse (nullable), subjects, review (nullable), approvalIds, nextAction | Specialists propose; Operations releases reviewed/approved responses |
| Approval | approvalId, subject, scope, status, decision (nullable), requestedAt, decidedAt (nullable), operatorId (nullable), reason (nullable), reviewId | Human decision and scope; never an execution authorisation for real transactions |
| TraceEvent | eventId, runId (nullable), timestamp, actor, eventType, subject, parentEventId (nullable), executionMode, summary, result, approvalId (nullable) | Append-only audit, owned by wrd in B05 |

ItineraryItem contains itemId, productType, offerId, offerVersion,
priceBreakdownId, startAt, endAt, origin, destination, quantity, quotedPrice and
sourceIds. It is a wire snapshot of the G-04 item selection. Detailed transport,
stay/activity capabilities are supplied by referenced products in B03/B09; they
must not be guessed from this snapshot. Each sourceIds entry resolves to supplied
or persisted evidence. Repository-level reference integrity is a later integration
check, not something a standalone JSON schema can establish.

## Agent inputs, outputs and ownership

| Agent ID / class | Owner | Input | Output / use cases |
| --- | --- | --- | --- |
| operations / OperationsAgent | Jiaheng | External intake via B06; confirmed Case at the shared handle_case boundary; specialist AgentResult | Confirmation, coordination, entitlement and controlled response: UC-05, UC-07 |
| planning / TravelPlanningAgent | Moore | Confirmed CustomerCase + its TravelRequest; baseline ItineraryVersion for revisions; approved offers | AgentResult with version subjects, comparison and issues: UC-01, UC-02 |
| exception / CustomerExceptionAgent | wrd | Confirmed CustomerCase; disruption/complaint, current version and evidence | AgentResult with recovery/resolution subjects or referral: UC-03, UC-04 |
| supplier / SupplierPartnershipAgent | Jason | Confirmed SupplierCase + source offer; operator CampaignBrief in B16 | AgentResult with offer/pricing or campaign subjects: UC-06, UC-08 |

Common Python entry: `handle_case(case: dict) -> dict` validates Case on entry
and AgentResult on exit. Related records are obtained through injected adapters
and repositories in later implementations, not embedded as undeclared Case
fields. CampaignBrief, CampaignProposal, MemberOfferRule, ExceptionCase and
PlanComparison remain report-domain records whose full exchange schemas will be
added with B12/B14/B15/B16; the B01 subject references reserve these boundaries.
The eight B01 contracts do not imply those later workflows are implemented.

Shared ports exist for LLM extraction/drafting/explanation, entitlement,
constraint validation, pricing, review, access control, approved-offer lookup,
trace and approval storage. This is one application and one planned database,
with normal internal calls; no broker or separately deployed agent services.
The Reviewer is a shared service owned by wrd, not a fifth business agent.

## Business states and control rules

Case uses SM-01 names converted to uppercase snake case: CONFIRMED, ASSIGNED,
IN_PROGRESS, AWAITING_PLAN_ACCESS_DECISION, AWAITING_REQUESTER,
AWAITING_VERIFICATION, UNDER_REVIEW, AWAITING_HUMAN_APPROVAL,
READY_TO_RESPOND, HUMAN_ASSISTANCE, CLOSED, WITHDRAWN. WITHDRAWN is the
transport representation of the report's withdrawal closure path. A handoff does
not close the case. Delivery/persistence failure keeps the case open. Authorised
manual closure must retain its reason/evidence; it does not imply successful
Traveller delivery. Historical ROUTED is represented by ASSIGNED, not silently
accepted as another enum.

ItineraryVersion assessmentState follows the actual SM-02 model: DRAFT,
VALIDATING, INFEASIBLE, FEASIBLE, UNDER_REVIEW, REVISION_REQUIRED,
AWAITING_HUMAN_REVIEW, REVIEWED, REJECTED, HANDED_OFF. planStatus carries
DRAFT/PLANNED/ACTIVE/COMPLETED, a TravelPlan snapshot for later integration;
only PLANNED/ACTIVE count toward the Free membership limit. Lifecycle updates
must not rewrite immutable itinerary content; save new assessment/trace records
and retain history. FEASIBLE does not imply reviewed or approved.

SupplierOffer: DRAFT → UNDER_REVIEW → APPROVED, or
AWAITING_APPROVAL when restricted. Validation/pricing are actions, not separate
stored SupplierOffer states (SM-04); failures produce REVISION_REQUIRED,
REJECTED or EXPIRED. Material corrections increment materialVersion and clear
review/approval before reassessment. Only approved, unexpired offers are selectable.

AgentResult status is SUCCESS, FAILURE, APPROVAL_PENDING, REVISION_REQUIRED
or HUMAN_ASSISTANCE. SUCCESS means an internal step succeeded, **not** that
Operations may deliver it. FAILURE requires errors. APPROVAL_PENDING requires
requiresApproval=true and approval references. executionMode is STUB, FIXTURE
or REAL. STUB may only return FAILURE, and no stub pretends to call an LLM.

Approval PENDING requires null decision/operator/time/reason. DECIDED requires
a real supplied operatorId, timestamp, decision and reason. Decisions are APPROVE,
REQUEST_REVISION or REJECT. Silence and elapsed time do not constitute approval.
An approval must match subject ID, materialVersion and scope, follow current
review, and be durably saved. Revisions require new review and human decision.
requiresApproval is the declared obligation, not evidence that it was fulfilled.

The later implementation must also check deterministic results, membership,
ownership, freshness and approval validity at runtime. Structural validity is
necessary but insufficient for any feasible/approved/released business claim.
Schemas reject a transport-only FEASIBLE plan, but full category coverage,
connections, constraints and total calculations belong to B04/B09.

## Business rules reserved for implementation

- Free: at most two PLANNED/ACTIVE trips; each at most five inclusive calendar
  days. Active Paid members have no Free limits, no commercial ads and permitted
  route maps. Failed verification blocks protected actions (B07/B17).
- basePrice = round(supplierCost × (1 + markupRate), 2);
  sellingPrice = round(basePrice − discountAmount, 2);
  marginAmount = sellingPrice − supplierCost. Selling price is positive and
  configured minimum margin passes after rounding (B04/B08).
- One approved fixed AUD member discount; no stacking. UC-07 checks eligibility,
  UC-06 rechecks quotation and margin, UC-08 defines approved member-offer rules.
  Reusable supplier base prices are not overwritten (B16/B17).
- No automatic constraint relaxation. Unsupported hard constraints block an
  unqualified feasible claim. Source expiry is rechecked on read (B04/B09).
- Payment, refund, compensation, binding supplier commitment, legal/safety,
  publication/spending and other restricted decisions require human control.
  Real execution remains outside this prototype even when a proposal is approved.
- Unresolved classification/confidence or humanRequestCount >= 2 triggers Human
  Assistance. It is separate from scoped Human Approval (B06/B12/B15).

## Error vocabulary and handling

Exact error enum lives at `#/$defs/Error`. INVALID_CONTRACT and
MISSING_REQUIRED_FIELDS reject malformed data; UNCONFIRMED_REQUEST blocks
handoff. ACCESS_DENIED, VERIFICATION_FAILED and ENTITLEMENT_DENIED block
protected actions. OFFER_INVALID/OFFER_EXPIRED/MARGIN_FAILED,
NO_FEASIBLE_ITINERARY/UNSUPPORTED_CONSTRAINT/STALE_EVIDENCE and REVIEW_FAILED
request correction or escalation. APPROVAL_REQUIRED/APPROVAL_REJECTED do not
release restricted proposals. LOW_CONFIDENCE/HUMAN_ASSISTANCE_REQUIRED refer
to human handling. LLM_TIMEOUT/LLM_INVALID_OUTPUT/TOOL_UNAVAILABLE,
PERSISTENCE_FAILED/DELIVERY_FAILED report the failed step and permitted retry.
NOT_IMPLEMENTED is only the explicit framework stub outcome. Do not fabricate
success when a save, provider or delivery operation failed.

## Examples, testing and version changes

The 20 JSON files in `examples/` cover all eight schemas, four agents × success /
failure / approval-pending, and pending/decided approval. All are **synthetic
contract messages**, not resettable B03 fixtures, executed validations or team
approval evidence. The partial itinerary example intentionally remains DRAFT.
Price amounts follow the report's AUD 180 / 10% / AUD 198 / AUD 18 illustration;
AUD 15 is a fixture minimum margin, not a universal policy default.

Run the local-check commands in `README.md` or `README.zh-CN.md`. Tests check required fields, strict types,
formats, status/flag consistency, and fail-closed agent stubs. See
`B01_ACCEPTANCE.md` for recorded evidence and pending human review.

Never edit v1 incompatibly after sign-off. A breaking field/enum change requires
v2, schemaVersion change, migration notes and updated examples. Clarifications
and added optional fields require a documented minor revision and revalidation.
Keep old PLAN identifiers in mapping records; do not rewrite historical sources.
