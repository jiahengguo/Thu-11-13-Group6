# TripMate AI — Jira Cards B01–B20

Updated: 9 October 2026. All card content is in English. These are planning cards, not confirmation that Jira issues have been created or completed.

## Scheduling and assignment conventions

- Deadlines are proposed internal completion dates in Australia/Sydney, including review and card-level testing. They are not official course submission dates. The W11 integrated prototype is due on 21 October, before the 22 October lab.
- Assignees use the names from the project documents: Jiaheng, Moore, wrd, and Jason. Map them to verified Jira accounts when importing; these names are not account IDs.
- Prerequisites list direct blocking planning IDs. Work may start against agreed contracts or stubs, but a card cannot be Done until its required integrations pass. Map these IDs to actual Jira keys and create “is blocked by” links after import.
- B06 intake work begins in S1 and finishes in S2. B16 and B17 move to S3 so campaign and paid-benefit functionality is available before the W12 lab. Keep S4 for reliability, regression, and final delivery.
- Business approval states are application behaviour; they are distinct from Jira development workflow states.

## Card overview

| ID | Title | Assignee | Deadline | Sprint | Prerequisites |
| --- | --- | --- | --- | --- | --- |
| B01 | Define shared agent contracts, domain schemas, and requirement mappings | Jiaheng | 2026-10-10 | S1 | None |
| B02 | Set up the runnable web application and local database | Jason | 2026-10-10 | S1 | None |
| B03 | Create resettable supplier, traveller, and disruption fixtures | Jason | 2026-10-11 | S1 | B01, B02 |
| B04 | Implement deterministic pricing and itinerary constraint validators | Moore | 2026-10-12 | S1 | B01, B03 |
| B05 | Persist and display linked agent execution traces | wrd | 2026-10-12 | S1 | B01, B02 |
| B06 | Capture, confirm, and route traveller and supplier requests | Jiaheng | 2026-10-15 | S2 | B01, B02, B03, B05 |
| B07 | Enforce membership limits and protected case access | Jiaheng | 2026-10-16 | S2 | B03, B04, B06 |
| B08 | Validate supplier offers and calculate approved selling prices | Jason | 2026-10-16 | S2 | B03, B04, B05, B10 |
| B09 | Generate a complete itinerary from approved supplier offers | Moore | 2026-10-18 | S2 | B04, B05, B07, B08, B10 |
| B10 | Build proposal review and human approval controls | wrd | 2026-10-14 | S1 | B01, B02, B04, B05 |
| B11 | Integrate the four-agent workflow and freeze the Week 11 demo | Jason | 2026-10-21 | S2 | B06, B07, B08, B09, B10, B12 |
| B12 | Investigate a cancellation and propose a validated recovery | wrd | 2026-10-20 | S2 | B06, B08, B09, B10 |
| B13 | Compare feasible itineraries in Comfort, Value, and Budget modes | Moore | 2026-10-23 | S3 | B09 |
| B14 | Create confirmed plan revisions and compare immutable versions | Moore | 2026-10-25 | S3 | B06, B07, B09, B13 |
| B15 | Investigate complaints and prepare reviewed resolution recommendations | wrd | 2026-10-26 | S3 | B06, B08, B09, B10 |
| B16 | Evaluate supplier-based campaigns and record human approval | Jason | 2026-10-27 | S3 | B08, B10 |
| B17 | Apply paid route-map access, advertising rules, and member-offer eligibility | Jiaheng | 2026-10-28 | S3 | B07, B08, B09, B16 |
| B18 | Handle dependency failures and make manual retries safe | Jason | 2026-10-30 | S4 | B11 |
| B19 | Run release regression scenarios and record acceptance evidence | wrd | 2026-11-02 | S4 | B11, B13, B14, B15, B16, B17, B18 |
| B20 | Finalize setup instructions, model alignment, and contribution records | Moore | 2026-11-04 | S4 | B19 |

## Shared Definition of Done

All card acceptance criteria pass; implementation or documentation is reviewed by another member and integrated into the shared project; applicable success/failure tests and evidence are attached; relevant trace, permission, approval, and error rules are respected; affected contracts/models are updated; the result is reproducible without a card-introduced blocking defect.

Task cards also include a user story describing the person who benefits. Their issue type remains Task. Card-specific acceptance criteria below supplement the shared Definition of Done.

## B01 — Define shared agent contracts, domain schemas, and requirement mappings

**Assignee:** Jiaheng  
**Reviewer:** wrd  
**Deadline:** 2026-10-10 (Australia/Sydney)  
**Prerequisites:** None  
**Issue type / Epic:** Task / E-PLAT  
**Sprint / MoSCoW / Estimate:** S1 / Must-have / 6 hours  
**Requirement / Use case:** Shared architecture; UC-01–UC-08

**Description**

Agree the inputs, outputs, required fields, business states, error codes, evidence references, and approval flags used by all four agents. Deliver a versioned contract document and representative JSON examples. Reconcile the older PLAN identifiers with the current TP identifiers without silently renumbering requirements.

**User story**

As a developer integrating an agent, I want a shared contract and domain schema, so that my module can exchange validated data with the other agents.

**Acceptance criteria**

1. All four members approve the Case, TravelRequest, SupplierOffer, PriceBreakdown, ItineraryVersion, AgentResult, Approval, and TraceEvent schemas.
2. Examples include caseId, correlationId, source references, validation results, errors, and requiresApproval.
3. A documented mapping identifies confirmed and unresolved PLAN/TP references; each agent has a named owner.

**Test method**

Review the contracts together and validate representative success, failure, and approval-pending JSON messages against the agreed schemas.

**Definition of Done:** Shared Definition of Done plus every acceptance criterion above.

## B02 — Set up the runnable web application and local database

**Assignee:** Jason  
**Reviewer:** Moore  
**Deadline:** 2026-10-10 (Australia/Sydney)  
**Prerequisites:** None  
**Issue type / Epic:** Task / E-PLAT  
**Sprint / MoSCoW / Estimate:** S1 / Must-have / 6 hours  
**Requirement / Use case:** Shared platform

**Description**

Create the shared application skeleton, configuration template, local persistence, agent module boundaries, and startup instructions. Verify one real LLM call and provide an explicitly labelled fixture mode. Use one application and database rather than four independently deployed services.

**User story**

As a team member, I want a reproducible application setup, so that I can develop and demonstrate my agent in the shared environment.

**Acceptance criteria**

1. Another member can start the application from a clean checkout using the documented steps.
2. The web interface, backend, and local database are reachable; configuration templates contain no secrets.
3. A real LLM smoke call succeeds or its blocker is recorded; fixture mode is visibly distinguishable from real model execution.

**Test method**

Have another member reproduce startup, check persistence connectivity, and run the LLM/fixture smoke checks.

**Definition of Done:** Shared Definition of Done plus every acceptance criterion above.

## B03 — Create resettable supplier, traveller, and disruption fixtures

**Assignee:** Jason  
**Reviewer:** Moore  
**Deadline:** 2026-10-11 (Australia/Sydney)  
**Prerequisites:** B01, B02  
**Issue type / Epic:** Task / E-PLAT  
**Sprint / MoSCoW / Estimate:** S1 / Must-have / 4 hours  
**Requirement / Use case:** Shared data; UC-01–UC-08

**Description**

Build one controlled Sydney-to-Melbourne dataset in AUD, with transport, accommodation, activities, Free/Paid travellers, active plans, invalid offers, complaints, and cancellation events. Include expected outcomes and a reset operation. Mark all provider and transaction data as simulated.

**User story**

As a developer and demo presenter, I want repeatable test fixtures, so that I can reproduce normal and failure scenarios without editing the database manually.

**Acceptance criteria**

1. Fixtures cover valid and expired offers, missing fields, zero stock, membership limits, cancellation, complaint, and approval cases.
2. Entity references remain valid after reset.
3. Two consecutive resets restore identical baseline data without retaining earlier approvals or plan revisions.

**Test method**

Reset twice, compare baseline records, check referential integrity, and inspect the expected-outcome scenario list.

**Definition of Done:** Shared Definition of Done plus every acceptance criterion above.

## B04 — Implement deterministic pricing and itinerary constraint validators

**Assignee:** Moore  
**Reviewer:** Jason  
**Deadline:** 2026-10-12 (Australia/Sydney)  
**Prerequisites:** B01, B03  
**Issue type / Epic:** Task / E-PLAT  
**Sprint / MoSCoW / Estimate:** S1 / Must-have / 6 hours  
**Requirement / Use case:** TP-01; SUP-02; OPS-03

**Description**

Implement reusable functions for price rounding, margins, budget, inclusive calendar duration, schedule conflicts, transfer time, availability, and other applicable confirmed hard constraints. Return structured pass/fail results with rule identifiers. LLM suggestions must not override failed rules.

**User story**

As a Traveller, I want my itinerary checked by reproducible rules, so that recommendations respect my budget, timing, and other confirmed constraints.

**Acceptance criteria**

1. Shared validators return pass/fail, applied rule, and reason rather than unstructured text alone.
2. Prices use a consistent AUD basis and two-decimal rounding; duration is end date minus start date plus one.
3. Unsupported constraints are recorded and block an unqualified feasible claim instead of being silently ignored.

**Test method**

Use automated boundary tests for rounding, minimum margin, five/six days, exact/exceeded budget, overlapping times, transfers, and unavailable inventory.

**Definition of Done:** Shared Definition of Done plus every acceptance criterion above.

## B05 — Persist and display linked agent execution traces

**Assignee:** wrd  
**Reviewer:** Jiaheng  
**Deadline:** 2026-10-12 (Australia/Sydney)  
**Prerequisites:** B01, B02  
**Issue type / Epic:** Task / E-PLAT  
**Sprint / MoSCoW / Estimate:** S1 / Must-have / 6 hours  
**Requirement / Use case:** Shared trace; UC-05

**Description**

Store and retrieve trace events linking requests, agent handoffs, tool results, plan versions, review outcomes, approval decisions, and responses. Provide a case-level trace view that survives application restarts. Exclude secrets from recorded content.

**User story**

As an Operator, I want a linked history of agent decisions and evidence, so that I can explain outcomes and investigate failures.

**Acceptance criteria**

1. Events share a caseId/correlationId and retain source, timestamp, actor, result, and relevant version references.
2. A case trace remains queryable after restart.
3. A failed save is reported and cannot be presented as a successfully recorded approval or completed action.

**Test method**

Execute and query a representative case, restart the application, inject a save failure, and manually inspect the trace for missing links and secrets.

**Definition of Done:** Shared Definition of Done plus every acceptance criterion above.

## B06 — Capture, confirm, and route traveller and supplier requests

**Assignee:** Jiaheng  
**Reviewer:** wrd  
**Deadline:** 2026-10-15 (Australia/Sydney)  
**Prerequisites:** B01, B02, B03, B05  
**Issue type / Epic:** Story / E-OPS  
**Sprint / MoSCoW / Estimate:** S2 / Must-have / 8 hours  
**Requirement / Use case:** UC-05; OPS-02

**Description**

Implement the Operations intake flow: identify requester/source, check simulated identity and access, use structured LLM extraction, ask for missing information, obtain confirmation, and route cases. Prepare the final response through the controlled Operations gateway. Start the intake and confirmation portion during S1 so S2 remains manageable.

**User story**

As a Traveller or Supplier, I want to confirm a structured request and have it routed to the appropriate agent, so that my request is handled accurately.

**Acceptance criteria**

1. Missing required information or unconfirmed changes prevent specialist routing.
2. Confirmed requests preserve their source and route planning, exceptions, and supplier cases to the correct owner.
3. Unresolved classification uncertainty or humanRequestCount >= 2 leads to human assistance.
4. Only a reviewed and appropriately approved response is delivered; failed processing or delivery does not incorrectly close the case.

**Test method**

Automate required-field/routing checks; manually exercise planning, complaint, supplier, and low-confidence inputs and inspect confirmation and handoff traces. Check LLM structure and behaviour rather than exact wording.

**Definition of Done:** Shared Definition of Done plus every acceptance criterion above.

## B07 — Enforce membership limits and protected case access

**Assignee:** Jiaheng  
**Reviewer:** wrd  
**Deadline:** 2026-10-16 (Australia/Sydney)  
**Prerequisites:** B03, B04, B06  
**Issue type / Epic:** Story / E-OPS  
**Sprint / MoSCoW / Estimate:** S2 / Must-have / 6 hours  
**Requirement / Use case:** UC-07; OPS-03

**Description**

Implement backend entitlement decisions and ownership checks using verified simulated membership data. Check entitlements before planning and again against the returned plan. Explain Allowed, Denied, and VerificationFailed outcomes without modifying an itinerary to satisfy a rule.

**User story**

As a Traveller, I want an explained membership decision, so that I know whether my requested trip is permitted.

**Acceptance criteria**

1. A Free Member with two Planned/Active trips cannot activate another; five calendar days pass and six fail.
2. Post-planning checks use the latest verified membership and trip facts; Paid Members do not inherit Free-tier limits.
3. Unavailable membership evidence returns VerificationFailed and blocks protected actions.
4. A traveller cannot read or modify another traveller’s cases or plans; checks run on the backend.

**Test method**

Automate trip-count and duration boundaries, membership changes, verification failure, and cross-user access; demonstrate the rejection reason in the UI.

**Definition of Done:** Shared Definition of Done plus every acceptance criterion above.

## B08 — Validate supplier offers and calculate approved selling prices

**Assignee:** Jason  
**Reviewer:** Moore  
**Deadline:** 2026-10-16 (Australia/Sydney)  
**Prerequisites:** B03, B04, B05, B10  
**Issue type / Epic:** Story / E-SUP  
**Sprint / MoSCoW / Estimate:** S2 / Must-have / 8 hours  
**Requirement / Use case:** UC-06; SUP-01; SUP-02

**Description**

Implement Supplier offer extraction with source references, deterministic validity checks, configured pricing, margin assessment, review, and conditional human approval. Provide approved offers to Planning through a reusable lookup that rechecks expiry. Corrections must trigger renewed assessment.

**User story**

As an Operator, I want validated offers with reproducible prices and margins, so that planners use reliable commercial data.

**Acceptance criteria**

1. Missing fields, expired validity, zero stock, unsupported currency, or invalid terms prevent approval and record a reason.
2. basePrice, sellingPrice, and marginAmount follow the configured formulas and rounding; minimum margin must pass.
3. Only Approved, unexpired offers can be selected by Planning.
4. Material revisions clear earlier approval; restricted terms remain pending until an authorised human decision; source costs cannot be altered to bypass margin rules.

**Test method**

Automate extraction schema, validity, pricing, rounding, and margin cases; manually import valid/invalid offers and check approval/revision traces.

**Definition of Done:** Shared Definition of Done plus every acceptance criterion above.

## B09 — Generate a complete itinerary from approved supplier offers

**Assignee:** Moore  
**Reviewer:** Jason  
**Deadline:** 2026-10-18 (Australia/Sydney)  
**Prerequisites:** B04, B05, B07, B08, B10  
**Issue type / Epic:** Story / E-PLAN  
**Sprint / MoSCoW / Estimate:** S2 / Must-have / 8 hours  
**Requirement / Use case:** UC-01; TP-01; legacy PLAN mapping in B01

**Description**

Implement Travel Planning for the controlled Sydney-to-Melbourne scenario. Assemble transport, stays, and activities from eligible offers, run applicable hard-constraint checks, compute itemised costs, and return a reviewed itinerary through Operations. Record evidence and explain infeasibility without relaxing constraints.

**User story**

As a Traveller, I want a complete feasible itinerary, so that transport, stays, and activities fit my confirmed constraints.

**Acceptance criteria**

1. A feasible itinerary contains the required connected travel legs, accommodation, and selected activities.
2. Every applicable hard constraint passes before feasibility is claimed; total cost reconciles to components.
3. Selected resources include offer IDs, source references, retrieval/validity information, and validation results.
4. No-solution cases identify unmet constraints and next actions without silent relaxation; output passes shared review and post-planning membership checks.

**Test method**

Automate budget, overlap, transfer, expiry, and price reconciliation cases; run feasible and infeasible requests end to end.

**Definition of Done:** Shared Definition of Done plus every acceptance criterion above.

## B10 — Build proposal review and human approval controls

**Assignee:** wrd  
**Reviewer:** Jiaheng  
**Deadline:** 2026-10-14 (Australia/Sydney)  
**Prerequisites:** B01, B02, B04, B05  
**Issue type / Epic:** Story / E-PLAT  
**Sprint / MoSCoW / Estimate:** S1 / Must-have / 6 hours  
**Requirement / Use case:** Shared guardrails; UC-05; UC-06; UC-08

**Description**

Create a shared review service and Operator approval workspace for offers, plans, recovery recommendations, and campaign proposals. Bind decisions to the reviewed version and enforce the same approval checks on backend actions and Operations responses.

**User story**

As an Operator, I want to inspect reviewed proposals and record approval decisions, so that restricted commitments remain under human control.

**Acceptance criteria**

1. Failed evidence, calculation, or policy checks prevent a proposal from passing review.
2. Approve, Request revision, and Reject are recorded with actor, reason where applicable, timestamp, and version; no decision remains AwaitingApproval.
3. A material proposal change invalidates earlier approval and repeats checks.
4. Save failures and unauthorised users cannot produce an approved result; pending/rejected commitments cannot be communicated as approved.

**Test method**

Automate approval transitions, version invalidation, save failure, and backend permissions; manually demonstrate rejection, revision, and no-response states.

**Definition of Done:** Shared Definition of Done plus every acceptance criterion above.

## B11 — Integrate the four-agent workflow and freeze the Week 11 demo

**Assignee:** Jason  
**Reviewer:** Moore  
**Deadline:** 2026-10-21 (Australia/Sydney)  
**Prerequisites:** B06, B07, B08, B09, B10, B12  
**Issue type / Epic:** Task / E-DEMO  
**Sprint / MoSCoW / Estimate:** S2 / Must-have / 6 hours  
**Requirement / Use case:** W11 release; UC-01; UC-03; UC-05; UC-06; UC-07

**Description**

Integrate the request entry, itinerary result, Operator workspace, and trace view into one application. Replace demo-path specialist stubs with real implementations. Complete the planning-to-cancellation-recovery flow and save a reproducible w11-prototype tag. Jiaheng supports approximately three hours of UI integration.

**User story**

As a demo presenter, I want one integrated four-agent workflow, so that I can demonstrate the complete service from request to recovery.

**Acceptance criteria**

1. A reset dataset supports intake, membership, supplier assessment, planning, cancellation recovery, review, and controlled response without manual database edits.
2. The trace shows all four agents participating in the same case with linked handoffs.
3. A membership/constraint rejection and an approval-pending case are demonstrable.
4. The stable tagged version can be restarted and demonstrated before the 22 October lab.

**Test method**

Have all four members run the full workflow from reset data, inspect page and trace consistency, and reproduce the tagged version.

**Definition of Done:** Shared Definition of Done plus every acceptance criterion above.

## B12 — Investigate a cancellation and propose a validated recovery

**Assignee:** wrd  
**Reviewer:** Jiaheng  
**Deadline:** 2026-10-20 (Australia/Sydney)  
**Prerequisites:** B06, B08, B09, B10  
**Issue type / Epic:** Story / E-EXC  
**Sprint / MoSCoW / Estimate:** S2 / Must-have / 8 hours  
**Requirement / Use case:** UC-03; EXC-01

**Description**

Handle one simulated transport cancellation affecting an Active itinerary. Gather evidence, ask Supplier for eligible alternatives, coordinate Planning revalidation, and return a consolidated recovery recommendation through Operations. Preserve the original plan and approval boundaries.

**User story**

As a Traveller with a disrupted trip, I want a validated recovery proposal, so that I can understand feasible alternatives and their consequences.

**Acceptance criteria**

1. The cancellation references the affected itinerary item and supporting evidence.
2. Supplier and Planning contribute to the recovery proposal while existing confirmed constraints are preserved.
3. The proposal explains price and timing changes and records passed validation/review checks.
4. No alternative, conflicting evidence, or unavailable dependencies trigger clarification or human handling; restricted commitments require approval and no real rebooking/payment occurs.

**Test method**

Exercise cancellation with an alternative, no alternative, dependency failure, and approval-required outcomes; inspect all four agents’ linked trace events.

**Definition of Done:** Shared Definition of Done plus every acceptance criterion above.

## B13 — Compare feasible itineraries in Comfort, Value, and Budget modes

**Assignee:** Moore  
**Reviewer:** Jason  
**Deadline:** 2026-10-23 (Australia/Sydney)  
**Prerequisites:** B09  
**Issue type / Epic:** Story / E-PLAN  
**Sprint / MoSCoW / Estimate:** S3 / Should-have / 6 hours  
**Requirement / Use case:** UC-01; TP-01

**Description**

Add common comparison fields and ranking rules for the three travel modes. Explain the selected plan, eligible alternatives, and reasons excluded candidates failed. Keep hard-constraint filtering separate from preference ranking and advertising.

**User story**

As a Traveller, I want to compare feasible options in Comfort, Value, or Budget mode, so that I can choose using consistent trade-offs.

**Acceptance criteria**

1. At least one fixture yields two or more feasible alternatives.
2. Each mode ranks only candidates that already passed the same hard-constraint checks.
3. Comparisons show cost, timing, convenience, evidence, and trade-offs using common fields.
4. Advertising cannot alter eligibility or recommendation ranking.

**Test method**

Automate filtering/ranking with a fixed candidate set and manually compare all three modes and exclusion explanations.

**Definition of Done:** Shared Definition of Done plus every acceptance criterion above.

## B14 — Create confirmed plan revisions and compare immutable versions

**Assignee:** Moore  
**Reviewer:** Jason  
**Deadline:** 2026-10-25 (Australia/Sydney)  
**Prerequisites:** B06, B07, B09, B13  
**Issue type / Epic:** Story / E-PLAN  
**Sprint / MoSCoW / Estimate:** S3 / Should-have / 6 hours  
**Requirement / Use case:** UC-02; TP-02

**Description**

Accept a confirmed amendment through Operations, preserve the baseline, generate a separately identified successor version, rerun applicable checks, and display field-level differences. Keep the baseline current when an amendment is unconfirmed or infeasible.

**User story**

As a Traveller, I want to confirm a change and compare a new plan version, so that I understand its effect without losing the original plan.

**Acceptance criteria**

1. Unconfirmed amendments cannot release a revised plan.
2. A valid revision has a distinct ID and does not overwrite baseline content.
3. The comparison identifies changed requirements, resources, schedule, cost delta, constraints, and evidence.
4. The revision passes renewed membership, price, availability, and schedule checks; infeasible revisions explain failures and leave the baseline current.

**Test method**

Exercise successful, unconfirmed, and infeasible amendments; automate baseline preservation, unique version IDs, and comparison calculations.

**Definition of Done:** Shared Definition of Done plus every acceptance criterion above.

## B15 — Investigate complaints and prepare reviewed resolution recommendations

**Assignee:** wrd  
**Reviewer:** Jiaheng  
**Deadline:** 2026-10-26 (Australia/Sydney)  
**Prerequisites:** B06, B08, B09, B10  
**Issue type / Epic:** Story / E-EXC  
**Sprint / MoSCoW / Estimate:** S3 / Should-have / 6 hours  
**Requirement / Use case:** UC-04; EXC-02

**Description**

Investigate Operations-routed complaints using trip records, service evidence, applicable policies, and supplier terms. Request missing information through Operations and consult specialist findings. Return a reviewed recommendation or documented human referral.

**User story**

As a Traveller, I want an evidence-supported complaint recommendation, so that the operator can decide a fair response.

**Acceptance criteria**

1. Findings and recommendations reference available evidence and applicable terms.
2. Missing evidence leads to clarification; legal/safety concerns and unresolved low confidence lead to human handling.
3. Refund or compensation commitments remain blocked without recorded human approval.
4. Human referral is not recorded as resolution of the underlying complaint; final communication remains with Operations.

**Test method**

Run a routine complaint, an evidence-incomplete complaint, and a compensation request; inspect approval blocking, handoff, and case status.

**Definition of Done:** Shared Definition of Done plus every acceptance criterion above.

## B16 — Evaluate supplier-based campaigns and record human approval

**Assignee:** Jason  
**Reviewer:** Moore  
**Deadline:** 2026-10-27 (Australia/Sydney)  
**Prerequisites:** B08, B10  
**Issue type / Epic:** Story / E-SUP  
**Sprint / MoSCoW / Estimate:** S3 / Should-have / 8 hours  
**Requirement / Use case:** UC-08; SUP-03

**Description**

Use an Operator brief and Approved, unexpired offers to draft a simulated campaign, calculate channel costs, check budget and claims, and request approval. Store campaign/member-offer rules for later entitlement/pricing checks. Preview only; simulated responses must retain campaign and source references.

**User story**

As an Operator, I want an evaluated campaign proposal based on approved offers, so that I can approve a credible plan within budget.

**Acceptance criteria**

1. The brief specifies objective, audience, channel, dates, budget ceiling, and restrictions; selected offers retain evidence.
2. Deterministic costs and budget checks pass before review; unsupported claims or commercial advertising targeted at Paid Members fail.
3. Approve, Request revision, and Reject are version-linked; material changes invalidate earlier approval.
4. Approved member offers record eligible tiers, offers, fixed AUD discount, and validity; preview performs no publication/spending; simulated responses go to Operations with campaignId/source.

**Test method**

Test exact/over-budget costs, expired offers, unsupported claims, Paid advertising, revised approvals, and source-tagged simulated responses.

**Definition of Done:** Shared Definition of Done plus every acceptance criterion above.

## B17 — Apply paid route-map access, advertising rules, and member-offer eligibility

**Assignee:** Jiaheng  
**Reviewer:** wrd  
**Deadline:** 2026-10-28 (Australia/Sydney)  
**Prerequisites:** B07, B08, B09, B16  
**Issue type / Epic:** Story / E-OPS  
**Sprint / MoSCoW / Estimate:** S3 / Should-have / 6 hours  
**Requirement / Use case:** UC-07; OPS-03; UC-08/UC-06 integration

**Description**

Complete membership benefits in the shared UI and backend. Add an interactive map of simulated route points for entitled Paid Members, an ad-free Paid interface, and clearly labelled Free advertisements. Connect approved campaign discounts to entitlement and supplier price checks without live map/payment integration.

**User story**

As a Paid Traveller, I want entitled route-map access and an ad-free interface, so that my membership benefits are applied consistently.

**Acceptance criteria**

1. Backend entitlement checks permit the route map for active Paid Members and reject unauthorised access.
2. Paid Members see no commercial advertising; Free advertisements are labelled and do not affect rankings.
3. The map displays the plan’s simulated route points and supports basic interaction.
4. UC-07 checks approved member-offer eligibility and UC-06 recalculates final price/margin; discounts cannot stack, survive expiry, or overwrite reusable base prices.

**Test method**

Test Free/Paid backend access and UI behaviour; inspect map points; exercise expired/ineligible discounts and discounts that violate minimum margin.

**Definition of Done:** Shared Definition of Done plus every acceptance criterion above.

## B18 — Handle dependency failures and make manual retries safe

**Assignee:** Jason  
**Reviewer:** Moore  
**Deadline:** 2026-10-30 (Australia/Sydney)  
**Prerequisites:** B11  
**Issue type / Epic:** Task / E-PLAT  
**Sprint / MoSCoW / Estimate:** S4 / Should-have / 6 hours  
**Requirement / Use case:** Shared reliability; UC-05

**Description**

Add visible failure states for LLM timeouts/invalid output, unavailable tools, and failed persistence. Support deliberate manual retry with duplicate-request protection and preserve existing versions/approvals. Jiaheng supports approximately three hours of permission and request-protection work.

**User story**

As an Operator, I want clear failure information and safe retries, so that transient problems do not create duplicate or misleading outcomes.

**Acceptance criteria**

1. Timeouts, malformed outputs, tool failures, and save failures report the failed step and a permitted next action.
2. Retry does not create duplicate approval decisions, release blocked results, or overwrite the baseline plan.
3. Real model execution and fixture mode remain distinguishable in the interface and evidence.

**Test method**

Inject each failure, repeat the same request/retry, and verify stored entities, approval records, case states, and trace events.

**Definition of Done:** Shared Definition of Done plus every acceptance criterion above.

## B19 — Run release regression scenarios and record acceptance evidence

**Assignee:** wrd  
**Reviewer:** Jiaheng  
**Deadline:** 2026-11-02 (Australia/Sydney)  
**Prerequisites:** B11, B13, B14, B15, B16, B17, B18  
**Issue type / Epic:** Task / E-DEMO  
**Sprint / MoSCoW / Estimate:** S4 / Should-have / 6 hours  
**Requirement / Use case:** W12 release evaluation; UC-01–UC-08

**Description**

Consolidate existing card-level tests into three release scenario sets: planning/membership, disruption/complaint, and supplier/campaign. Map requirements to test evidence, repeat demonstrations from reset data, and report incomplete or failed acceptance criteria. Each member supplies evidence for their own module.

**User story**

As an Operator and assessor, I want reproducible acceptance evidence, so that I can verify which core capabilities actually work.

**Acceptance criteria**

1. All three scenario sets include successful and meaningful failure/approval-waiting paths.
2. Each scoped requirement links to a test result, trace, screenshot, or demonstration record and a responsible contributor.
3. All Must acceptance criteria pass; unresolved Should items and defects are explicitly listed.
4. The stable release completes two consecutive demonstrations from reset data without a blocking defect.

**Test method**

Run the scenario matrix, inspect automated/manual results and trace links, and reproduce the demo twice; record actual results rather than assumed passes.

**Definition of Done:** Shared Definition of Done plus every acceptance criterion above.

## B20 — Finalize setup instructions, model alignment, and contribution records

**Assignee:** Moore  
**Reviewer:** Jason  
**Deadline:** 2026-11-04 (Australia/Sydney)  
**Prerequisites:** B19  
**Issue type / Epic:** Task / E-DEMO  
**Sprint / MoSCoW / Estimate:** S4 / Should-have / 4 hours  
**Requirement / Use case:** Shared delivery; Stage 1–Stage 2 traceability

**Description**

Prepare the final runbook, simulation boundaries, supported functionality, known limitations, requirement-to-implementation mapping, model updates, and individual contribution record. Start documentation alongside implementation and finalize it against the accepted release.

**User story**

As an assessor or new team member, I want accurate setup and contribution documentation, so that I can reproduce the prototype and understand its design and ownership.

**Acceptance criteria**

1. Another member can start and reset the accepted release using the runbook.
2. Documentation states which data/actions are simulated, which features pass acceptance, and which remain incomplete.
3. Model/interface changes and unresolved requirement mappings are documented consistently with the implementation.
4. All four members confirm contribution evidence; documentation links to the accepted version and test results.

**Test method**

Have another member reproduce setup and a demo scenario; cross-check the final documents, models, requirement mapping, and contributions against the accepted release.

**Definition of Done:** Shared Definition of Done plus every acceptance criterion above.

## CSV import notes

The companion `Jira_Starter_Backlog.csv` contains the same 20 cards. Map Summary to the issue title, Description to the issue description, and Due Date to the Jira deadline field using the date format `yyyy-MM-dd`. Assignee and Reviewer require verified account mapping. User Story and Dependencies are also included inside Description, so those details survive import even if separate custom fields are unavailable. Create the six Epics and four sprints, then map planning aliases to their actual Jira identifiers. The CSV does not itself create dependency links. The additional columns `更改内容` (change record) and `交接内容` (handoff notes) record implementation evidence and follow-up responsibilities. Map them to matching multiline custom fields when available, or retain their contents as issue notes. B01 is populated as of 10 October 2026; its four-member schema approval remains pending.

## Capacity and release checks

The estimates remain 126 hours: Jiaheng 26, Moore 30, wrd 32, and Jason 38. With approximately three hours of support on each of B11 and B18 transferred to Jiaheng, the effective distribution is Jiaheng 32, Moore 30, wrd 32, and Jason 32. Do not count those support hours twice. Sprint totals are S1 34, S2 44, S3 32, and S4 16 hours. B06 preparation and documentation may begin earlier while their acceptance deadlines remain unchanged.

Deadlines assume each member can contribute approximately 12–14 hours per week. At planning, confirm actual availability, allocate review time, and revise future dates if assumptions fail. All direct prerequisite deadlines precede their dependent card deadlines.
