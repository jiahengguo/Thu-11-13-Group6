# UC-08 - Plan, Evaluate, and Approve a Marketing Campaign

## Identification

Author: Jason | Level: User goal | System boundary: TripMate AI

Primary requirement: SUP-03. Ad-hoc requirement: SUP-AH-02. Owner: Supplier Partnership Agent. Related use cases: UC-06 supplies approved supplier offers; UC-05 handles source-tagged Campaign Responses; UC-07 evaluates approved member-offer eligibility. These are business dependencies, not an instruction to draw a particular include/extend relationship.

The assigned personal diagram chain remains SUP-AH-01 -> UC-06 -> AD-04 / SD-04 / SM-04. This additional specification does not require a second set of personal diagrams under the retrieved Stage 1 plan.

## Goal

Prepare a supplier-data-based marketing campaign, evaluate its evidence and budget, and obtain a recorded Human Founder/Operator decision before it can be used for an authorised campaign action.

## Actors and supporting components

Primary external actor: Human Founder/Operator, which defines the campaign brief and approves, requests revision or rejects the proposal.

Supporting external actor: Travel Service Provider, only when supplier clarification is needed through Operations. A real Advertising Channel is relevant to a later explicitly authorised publication action; real channel integration is outside the base prototype.

Internal collaborators: Supplier Partnership Agent, LLM drafting function, supplier offer data, deterministic campaign evaluation functions, Reviewer/Guardrail, local campaign/trace storage and Operations for supplier communication and Campaign Responses. These components are inside the TripMate AI system boundary.

## Trigger

The Human Founder/Operator submits a campaign brief requesting a proposal based on relevant supplier offers, or submits a revision to an existing brief.

## Preconditions

- The operator has the required access to request and decide campaign proposals.
- The system has configured permitted channels, content restrictions and a simulated cost basis for the selected channel.
- Supplier data is accessible to the Agent. The existence of a suitable offer is not guaranteed; no suitable data follows A2.
- The brief can be incomplete initially; missing information follows A1 rather than being guessed.

## Success conditions

- An Approved campaign proposal is saved with the brief, selected supplier references, draft content, channel/dates, estimated cost breakdown, passed evaluation/review and human decision.
- The proposal is available to the operator for preview or an authorised simulated campaign action.
- No advertisement has been externally published and no real funds have been spent merely because the proposal was approved.

## Failure conditions and minimum guarantee

An incomplete or failed proposal stays Draft or RevisionRequired with reasons. A proposal awaiting a human decision stays AwaitingApproval. Human rejection produces Rejected. A tool or save failure prevents a successful approved result and supports manual retry. Unapproved or materially changed proposals cannot be used as approved campaign material.

## Main success scenario

1. The operator provides the objective, audience, permitted channel, campaign dates, budget ceiling and content restrictions.
2. Supplier Partnership checks the brief for completeness and saves a Draft campaign with a campaign ID.
3. The Agent selects relevant Approved, unexpired supplier offers and records their prices, availability, validity, terms and source references. The campaign dates must fit the offers' applicable promotion validity; otherwise the proposal is revised.
4. The LLM drafts campaign content and a proposal explaining the selected offers, audience and channel in relation to the objective. Sources accompany factual claims.
4a. If a member offer is included, record the applicable supplier offers, eligible membership tiers, one fixed AUD discount and validity period. Include these rules in the proposal for review and human approval.
5. A deterministic function calculates the estimated campaign cost from configured simulated cost items, and checks the budget ceiling, permitted channel, campaign dates and consistency of advertised prices/terms with supplier data.
6. Reviewer/Guardrail checks evidence, claims, calculation results and configured content/privacy restrictions. On pass, the proposal enters AwaitingApproval and is presented to the operator with its cost breakdown and assumptions.
7. The operator approves the reviewed proposal. The Agent saves the decision, proposal and trace, and sets the campaign to Approved only after the save succeeds.
8. The system returns the approved proposal to the operator for preview. External publication and real spending are not executed by this base scenario.

## Alternative and error flows

### A1 - Incomplete or ambiguous brief (steps 1-2)

Ask the operator for the missing objective, dates, permitted channel, budget or restriction. Keep Draft until the brief is complete. The LLM must not invent a budget or permission to use a channel.

### A2 - No suitable supplier data (step 3)

Explain why offers cannot be used, such as expiry, unavailable inventory, inconsistent price basis or unsuitable dates. Keep the campaign Draft or RevisionRequired and ask the operator to change the brief or provide suitable data. Supplier clarification goes through Operations. Do not fabricate a supplier offer or alter an approved price.

### A3 - Budget, dates or evidence check fails (steps 5-6)

Set RevisionRequired and record the failed checks. The Agent may draft a corrected proposal within the existing brief, such as reducing planned campaign units. A higher budget ceiling or changed constraint requires operator confirmation. Repeat evaluation and review; do not silently relax the failed rule.

### A4 - Human decision (step 7)

Approve proceeds to save. Request revision records the requested changes, clears prior approval and repeats the relevant drafting, evaluation and review steps. Reject saves Rejected and the reason. No decision leaves AwaitingApproval. Human approval cannot substitute for missing required evidence or a failed deterministic check; any permitted rule change must first be explicitly recorded and the proposal reassessed.

### A5 - Supplier data or campaign content changes

If selected offers become unsuitable, or campaign content, channel, dates or budget materially changes, mark RevisionRequired and clear prior approval. Refresh the evidence and repeat evaluation, review and human approval. The prototype can check this when the proposal is reopened or used; a background monitoring/notification service is not required.

### A6 - LLM, evaluation or save error

Show the error and do not return a successfully approved campaign. Keep the current business state with an error and allow manual retry. Local campaign data and trace may be saved in a normal database transaction; no distributed recovery mechanism is required.

### A7 - Optional simulated campaign response after approval

If the prototype demonstrates a simulated campaign, a generated response records campaignId and sourceChannel and is sent to Operations. UC-05 confirms the request, routes it and controls external replies. A response does not transfer campaign design or budget ownership to Operations. This demonstration is optional to the base approval scenario.

### A8 - Request for real publication or spending

The base prototype does not execute the action. A future implementation must obtain explicit human authorisation for the publication/spending action and use an approved channel integration. Approval of a draft proposal must not be treated as blanket authorisation to spend or publish.

## Business rules

- BR-08-01: Supplier Partnership owns supplier-data-based campaign planning, evaluation and approval coordination; Operations owns Campaign Response intake under UC-05.
- BR-08-02: Use approved supplier evidence. The LLM may draft and explain but cannot invent prices, discounts, availability, permissions or guaranteed campaign outcomes.
- BR-08-03: estimatedTotalCost = sum(plannedUnits x configuredUnitCost) + recordedFixedCosts. All items use the same AUD basis in the prototype. Count each charge once, and do not assume an unknown cost is zero.
- BR-08-04: Estimated cost must not exceed the confirmed ceiling. Planned dates/channel and advertised prices/terms must pass configured checks.
- BR-08-05: Reviewer pass and a recorded human approval are required for an Approved campaign. A material change invalidates that approval.
- BR-08-06: Proposal approval, simulation, external publication and real spending are distinct actions. External publication and spending require explicit human authorisation.
- BR-08-07: Record sources, assumptions, cost items, failed checks, revisions, reviews and decisions. Do not claim predicted clicks, conversions or revenue without an identified supporting basis; such prediction is not required here.

- BR-08-08: UC-08 defines and obtains approval for member-offer rules. UC-07 determines eligibility; UC-06 or the purchasing process checks the final price and margin. Campaign approval alone does not establish an individual customer's eligibility or guarantee a viable discounted quote.
- BR-08-09: Paid Members do not receive commercial advertising. Eligibility for a member offer is separate from permission to receive advertisements. Deterministic audience checks and Reviewer review must enforce this distinction before proposal approval or simulation.
- BR-08-10: Campaigns may reference an existing approved temporary-entitlement mechanism. New or permanent entitlements require separate Human Approval and a controlled Entitlement Catalogue update; UC-08 does not directly rewrite membership policy.

## Tools and data

- CampaignBrief: objective, audience description, permitted channel, start/end dates, budget ceiling and restrictions.
- Approved SupplierOffer and PriceBreakdown records from UC-06, with validity and source references.
- LLM drafting function: brief + supplier evidence -> campaign draft, proposal explanation and source references.
- Simulated channel-cost configuration and deterministic evaluation function: proposal -> total estimated cost, check results and reasons.
- Reviewer/Guardrail: evidence, content and evaluation checks -> pass or revision reasons.
- Operator decision form: Approve / Request revision / Reject and comments.
- Local Campaign record and Agent Trace: brief, proposal, evidence, estimated cost, status, review and decision.
- Optional CampaignResponse record: campaignId, sourceChannel and response content, handed to Operations.

All of these responsibilities can be implemented as functions and records in the same application. This specification does not require advertising APIs, payment integrations, predictive models or extra deployments.

- ApprovedMemberOfferRule: rule ID/version, applicable supplier offer IDs, eligible tiers, fixed AUD discount, validity and human approval reference. References to existing approved entitlement mechanisms are optional.

## Approval conditions

Every campaign proposal requires human approval after review. A change to budget ceiling, content restrictions or permitted channel requires operator confirmation. External publication or actual spending additionally requires explicit action authorisation. The prototype ends at the approved proposal or optional simulation.

## Acceptance criteria

- AC-UC08-01: Given a brief without a budget ceiling or dates, the system requests the missing information and does not submit an invented brief for approval.
- AC-UC08-02: Given an expired/unapproved offer or unsupported advertised price, the campaign is blocked for revision with a reason and does not become Approved.
- AC-UC08-03: Given 20 simulated campaign units at AUD 2.00 each and a fixed cost of AUD 10.00, total estimated cost is AUD 50.00. A ceiling of AUD 60.00 passes the budget check; a ceiling of AUD 45.00 fails. These figures are fixtures, not agreed channel pricing.
- AC-UC08-04: Given an unsupported supplier claim or a failed content rule, Reviewer requests revision and no approval is inferred.
- AC-UC08-05: Approve saves the reviewed campaign; Request revision clears approval and repeats checks; Reject records the reason; no decision remains AwaitingApproval.
- AC-UC08-06: A tool/save failure does not return an approved result. A successfully approved proposal includes supplier evidence, cost breakdown and the recorded human decision.
- AC-UC08-07: Material changes to the proposal or selected supplier data require reassessment and fresh approval before further use.
- AC-UC08-08: Approving or previewing the proposal does not publish an advertisement or spend real money. If a simulated response is produced, it includes campaign/source references and goes to Operations.

- AC-UC08-09: An approved member offer preserves its rule, validity and approval reference. UC-07 supplies the eligibility decision and UC-06 or the purchasing process validates the discounted price before use.
- AC-UC08-10: A commercial-advertising proposal targeting Paid Members fails audience checks and requires revision, even if those members qualify for a member offer.

## Assumptions and scope

This prototype uses simulated offers and channel costs, one AUD cost basis and simple deterministic checks. The team must confirm permitted channels, cost units, content restrictions and campaign approval conditions. Audience descriptions use supplied simulated/non-personal data; personalised ad targeting and live ad-platform integration are not part of this base scenario. The current project requirement remains the product authority and should be checked against this proposed specification before final submission.
