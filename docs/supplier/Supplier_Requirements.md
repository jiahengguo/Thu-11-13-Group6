# Supplier Partnership - Prototype Scope

Author: Jason | Stage 1 | SUP-01 / SUP-02 / SUP-03 / SUP-O1

## 2.5 Supplier Partnership Agent

- Assesses supplier offers received through the Operations Agent and prepares approved offers for internal travel planning.
- Uses an LLM to extract supplier information, identify missing or ambiguous details, and explain findings with supporting evidence.
- Uses deterministic functions to validate offer details and calculate selling prices and margins.
- Submits offers and price breakdowns to the Reviewer/Guardrail for evidence, calculation and policy checks.
- Plans and evaluates marketing campaigns using relevant approved supplier data, including eligible products, availability, prices and commercial terms.
- Uses an LLM to draft campaign content and explain the proposal, while deterministic checks evaluate budget limits and consistency with supplier data.
- Requests Human Founder/Operator approval for campaign proposals, binding agreements, restricted commercial terms and financial commitments. External campaign publication or real spending requires explicit approval.
- Routes supplier clarification requests and proposed external messages through Operations. Campaign Responses are handed to Operations with their campaign and source references for handling under UC-05.
- Records offer outcomes, price breakdowns, campaign evaluations, review results and approval decisions in the Agent Trace.
- Cannot independently enter contracts, spend funds, publish campaigns or override failed validation and pricing rules.

## 3.5 Core features

### SUP-01 - Supplier offer import and validation (Core)

- Operations supplies a confirmed SupplierCase and simulated supplier offer source.
- The LLM extracts supplier/product identifiers, availability, supplier price, currency, validity period and cancellation terms, and identifies missing or ambiguous information. Extracted fields remain linked to the source.
- Deterministic checks require the configured fields, an eligible supplier, positive available quantity, a non-negative price, an unexpired validity period and permitted terms. Initial prototype data uses one consistent AUD price basis with all mandatory charges already included. Unknown charges or unsupported currency require correction.
- Failed checks produce RevisionRequired with a reason. Operations coordinates clarification and confirms supplier-supplied corrections before reassessment.
- Only Approved, unexpired offers may be selected by Travel Planning. A material correction clears previous review/approval and repeats assessment. Expiry is checked when the offer is retrieved; automatic notifications and background monitoring are not required for this prototype.
- Save the source, extracted fields, status and key decisions. A tool or save failure prevents approval and is shown for manual retry.

### SUP-02 - Selling price and margin calculation (Core)

- A deterministic function calculates basePrice = round(supplierCost x (1 + markupRate), 2); sellingPrice = round(basePrice - discountAmount, 2); marginAmount = round(sellingPrice - supplierCost, 2). The base assessment uses discountAmount = 0. A customer quote may apply one approved fixed AUD discount; discounts are not stacked. The final price must be positive and the configured minimum margin must pass after any discount. Both values refer to the same quoted quantity and AUD price basis.
- The configured minimum margin amount must pass after rounding. Missing pricing configuration or a failed margin rule produces RevisionRequired; the LLM cannot change the recorded supplier cost to make the calculation pass.
- PriceBreakdown contains supplierCost, markupRate, basePrice, discountAmount, sellingPrice, marginAmount, currency and the applied configuration reference. Customer-specific quotes additionally record the approved UC-08 rule and UC-07 eligibility decision. Missing or unverifiable required eligibility pauses the discounted quote; it does not invalidate the underlying approved supplier offer.
- Reviewer/Guardrail checks source consistency, the calculated values and applicable rules. Failure returns the offer for revision.
- Binding supplier prices, agreements, restricted terms and financial commitments require recorded human approval. The human can Approve, Request revision or Reject. Requested revision repeats the checks; it never flows directly to Approved. No decision leaves the offer AwaitingApproval.
- Save the approved outcome and trace before returning the offer to Operations for its normal communication checks. Internal approval is not a booking, payment or signed agreement.

### SUP-03 - Supplier-data-based marketing campaign planning and evaluation (Core)

- The Human Founder/Operator provides the campaign objective, audience, permitted channel, campaign dates, budget ceiling and content restrictions.
- Supplier Partnership selects relevant Approved, unexpired supplier offers from the simulated dataset. It retains the source references, prices, availability, validity and commercial terms used in the proposal. Unclear information is clarified through Operations.
- The LLM drafts a campaign proposal containing the selected offers, target audience, channel, dates, draft promotional content and an explanation of how the proposal supports the stated objective. It must not invent availability, discounts, supplier commitments or unsupported claims.
- The Agent uses simple configured simulated channel costs to prepare an estimated budget. Deterministic functions calculate total planned cost and check it against the budget ceiling, permitted channel and campaign dates. Advertised supplier prices and terms must agree with the selected offers; member-offer rules record eligible tiers, applicable offers, one fixed AUD discount and a validity period, and require human approval. UC-07 decides eligibility; UC-06 or the purchasing process validates the final price and margin. Paid Members must not receive commercial advertising even when eligible for a member offer.
- Reviewer/Guardrail checks the supplier evidence, calculations, advertising claims and configured content/privacy restrictions. A failed check returns the proposal for revision; a passing proposal goes to the Human Founder/Operator for approval.
- The human can Approve, Request revision or Reject. A material change to campaign content, offers, dates, channel or budget clears the previous approval and repeats evaluation and review. No human response is treated as approval.
- Save the proposal, cost breakdown, evaluation, source references, review and human decision in the Agent Trace. Approval of the proposal does not itself publish an advertisement or spend money. The prototype may preview or simulate an approved campaign; any external publication or real spending needs explicit authorisation for that action.
- Any simulated Campaign Response carries its campaign ID and source channel to Operations for UC-05 intake and coordination. Operations does not take ownership of campaign planning, budget evaluation or approval.

## 4.4 Optional feature

### SUP-O1 - Supplier reliability summary (Optional)

The Agent may summarise simulated completed supplier outcomes for human review. A deterministic function counts eligible final outcomes and supplier cancellations for a stated supplier and reporting period. Supplier-cancellation rate = supplier cancellations / eligible final outcomes x 100%. Zero outcomes produce Not applicable. The LLM explains the recorded counts and limitations without fabricating evidence or assigning an unsupported reliability rating. Reviewer checks the result before display. The feature does not change contracts, supplier eligibility or approved offers.

This is a small scorecard implementation: recorded counts plus one rate and an evidence-based explanation. Weighted scores, predictions and automatic supplier suspension are not required.

## 5.4 Ad-hoc requirements

### SUP-AH-01 - Supplier offer assessment and margin validation

The Supplier Partnership Agent should assess supplier offers received through Operations and prepare reliable offers for internal planning. It should use an LLM to extract the supplier, product, availability, price, validity and cancellation details while retaining the source. Deterministic checks should identify missing, ambiguous, expired or otherwise invalid information. The Agent should request correction through Operations and keep the offer unavailable until the corrected information has been confirmed and checked.

For a valid offer, the system should calculate the selling price and margin using configured rules and create a PriceBreakdown. Reviewer/Guardrail should check the evidence, arithmetic and policy conditions. Restricted decisions should wait for Human Founder/Operator approval. A requested revision should repeat assessment; rejection should be recorded with a reason. Only an approved, unexpired offer should be available to Travel Planning. The system should retain a simple trace and return outcomes through Operations. The prototype uses simulated data and does not execute bookings, contracts or payments.


### SUP-AH-02 - Supplier-data-based campaign planning and evaluation

The Supplier Partnership Agent should use approved and unexpired supplier offers to prepare a marketing campaign proposal based on a Human Founder/Operator campaign brief. The proposal should include selected offers, target audience, channel, dates, promotional content and estimated cost. Deterministic checks should verify the budget, campaign dates, supplier prices and terms. Reviewer/Guardrail should verify evidence and advertising restrictions. The Human Founder/Operator must approve, request revision or reject the proposal before any authorised campaign action. Material changes require renewed checks and approval. Where a proposal includes a member offer, it should record the applicable offers, eligible membership tiers, fixed discount and validity period for human approval. UC-07 determines eligibility; UC-06 or the purchasing process validates the resulting price and margin. Decisions and evidence should be traceable. External publication and real spending remain outside the prototype unless separately authorised.
