# UC-06 - Source Supplier Inventory and Validate Margin

## Identification

Author: Jason | Level: User goal | System: TripMate AI

Requirements: SUP-01, SUP-02, SUP-AH-01. Diagrams: AD-04, SD-04, SM-04. Related use cases: UC-05, UC-07, UC-08.

## Goal

Assess a supplier offer and return an approved SupplierOffer and PriceBreakdown for internal planning.

## Actors and internal collaborators

Primary actor: Travel Service Provider, which supplies and corrects information through Operations. Supporting actor: Human Founder/Operator. Operations, Supplier Partnership, the LLM, Validation/Pricing functions and Reviewer are internal components, not external actors in the overall TripMate AI use-case diagram.

## Trigger

Operations forwards a confirmed supplier case or confirmed correction to Supplier Partnership.

## Preconditions

- Operations has performed the required intake/access checks and confirmed the supplied information under UC-05.
- The prototype contains simulated supplier data and configured validation, markup, minimum-margin and approval rules.
- Specialist validation may still fail after intake. Service availability is not assumed to guarantee success.

## Success conditions

- The offer is Approved with a saved PriceBreakdown, Reviewer pass and any required human approval.
- The outcome and key decisions are saved and returned to Operations. Only approved and unexpired offers are selectable.
- Operations retains responsibility for external delivery and SupplierCase closure.

## Failure conditions

Failed information, validation, margin or review checks leave the offer RevisionRequired. A human rejection produces Rejected. Pending approval leaves AwaitingApproval. A tool/storage error retains the current state with an error and prevents publication; manual retry is allowed. Failed assessment does not close Operations' case.

## Main success scenario

1. Operations forwards the confirmed case and supplier source.
2. Supplier Partnership creates or updates a Draft offer; the LLM extracts fields, source evidence and uncertainties.
3. Validation/Pricing functions validate fields, supplier eligibility, availability, expiry, price basis and terms.
4. The functions calculate selling price and margin, check the minimum margin and return a PriceBreakdown.
5. The offer enters UnderReview. Reviewer checks evidence, calculations and rules and returns a pass and the applicable approval requirement.
6. When required, the offer enters AwaitingApproval and the human approves it. Otherwise the routine internal-use policy permits continuation.
7. Supplier Partnership saves the Approved outcome, PriceBreakdown and key trace records. A save failure does not make the offer available.
8. Supplier Partnership returns the result to Operations; UC-05 handles the external response.

## Alternative and error flows

### A1 - Information, validation or margin failure (steps 2-4)

Save RevisionRequired with the specific issue and return it to Operations. Operations coordinates a permitted correction, obtaining confirmation for supplier facts. On a confirmed correction, clear previous review/approval, set Draft and repeat steps 2-7. The Agent cannot invent supplier facts or override a failed rule. If no correction is supplied, the offer remains unavailable; it need not automatically time out or be reassigned.

### A2 - Reviewer failure (step 5)

Return RevisionRequired with the failed check and follow A1. No failed review can proceed to approval.

### A3 - Human decision (step 6)

Approve continues to save. Request revision follows A1. Reject saves Rejected and the reason and returns the outcome to Operations. No decision leaves AwaitingApproval. An approval cannot override failed validation or margin checks.

### A4 - Expiry or material correction after approval

Check the current time against validUntil whenever an offer is selected. An expired offer is unavailable and may be marked Expired during that read. A material correction moves the offer to RevisionRequired, clears approval and repeats assessment after confirmation. The prototype does not need a background expiry service or notifications to other Agents. Confirmed bookings are outside this use case.

### A5 - LLM, function or save error

Show the error, keep the existing business state and do not return an approved result. Operations or the operator can retry manually. No automatic recovery queue, event bus or distributed commit protocol is required. For local storage, a normal transaction can save the offer and trace together.

### A6 - External delivery fails

Operations keeps the case open and handles the failure under UC-05. Supplier Partnership does not implement a second delivery system.

### A7 - Member-specific quote validation

When a customer quote requests a member discount, consume the approved UC-08 rule and the current UC-07 eligibility decision. Verify the rule approval, applicable offer, validity, currency and quote quantity. Missing or unverifiable required evidence pauses that quote and is returned to Operations for clarification. An ineligible customer receives no discount and an explanation through Operations. An eligible customer receives the approved fixed discount only after the final positive-price and minimum-margin checks pass. A failed discounted margin check blocks that quote for revision; neither the LLM nor human approval can silently alter supplier cost or override a failed rule.

Save a separate customer-specific PriceBreakdown with its rule and eligibility references. Do not overwrite the reusable supplier offer's base price or set an otherwise valid SupplierOffer to RevisionRequired merely because one customer's discounted quote fails. Material changes to the underlying supplier offer still follow A4. AD-04, SD-04 and SM-04 model the base offer assessment and SupplierOffer lifecycle; this conditional quote extension reuses its deterministic pricing function.

## Business rules and approval conditions

- Operations owns all external messages and supplier confirmation.
- LLM extraction/explanation does not replace deterministic validation or arithmetic.
- supplierCost, sellingPrice and marginAmount use the same quantity and AUD basis. Supplier cost includes known mandatory charges; unknown values must be corrected.
- basePrice = round(supplierCost x (1 + markupRate), 2); sellingPrice = round(basePrice - discountAmount, 2); marginAmount = round(sellingPrice - supplierCost, 2). The base assessment uses discountAmount = 0. A customer quote may apply one approved fixed AUD discount; discounts are not stacked. The final price must be positive and the configured minimum margin must pass after any discount.
- Reviewer pass is mandatory. Human approval is required for binding prices, agreements, restricted terms, financial commitments and any other configured restricted decision.
- A material revision clears the previous approval and repeats assessment. Saving an approval does not execute a transaction.
- Only Approved and unexpired offers are selectable. Tool errors and incomplete records are not approval.

## Tools and data

- LLM extraction function: source text -> structured fields, evidence, uncertainty.
- validateAndPrice(fields, config): -> pass + PriceBreakdown, or failure + reason. This may call two ordinary functions internally.
- review(fields, source, breakdown): -> pass/failure, reasons and approvalRequired.
- Human decision form: Approve / Request revision / Reject and reason.
- Local offer storage and trace: offer ID, case ID, source, fields, status, breakdown, review, approval and timestamped events.

The diagram separates responsibilities, not deployments. One application with functions/modules and local SQLite storage can implement this model.

- Customer quote inputs: approvedMemberOfferRule and UC-07 eligibility decision, including rule/version references and decision basis. PriceBreakdown stores basePrice and discountAmount; discountAmount is zero for the base supplier assessment.

## Acceptance criteria

- AC-01: A missing field, invalid supplier, unavailable item or expired offer does not reach approval; the reason is returned through Operations.
- AC-02: With supplierCost=180 AUD, markupRate=10% and minimum margin=15 AUD, the calculation returns sellingPrice=198 and marginAmount=18. With a 5% markup, sellingPrice=189 and marginAmount=9, so the margin check fails. These are test fixtures, not agreed business defaults.
- AC-03: Reviewer failure produces RevisionRequired and no approved output.
- AC-04: A restricted offer without a human decision remains AwaitingApproval. Approve, Request revision and Reject have the three specified outcomes.
- AC-05: A confirmed correction clears old decisions and repeats extraction/checks before approval.
- AC-06: A successfully saved approved result includes the breakdown and trace; a save/tool error cannot produce an approved output.
- AC-07: Reading an expired Approved offer excludes it from selection. No scheduler is needed to pass this check.
- AC-08: Every supplier-facing message passes through Operations, which retains case delivery and closure responsibilities.

- AC-09: With cost=180 AUD, basePrice=198, approved discount=5 and minimum margin=15, the final price is 193 and margin is 13. The discounted quote fails while the underlying approved offer remains unchanged.
- AC-10: Missing eligibility evidence pauses the discounted quote. A confirmed ineligible customer is quoted the base price with an explanation; no member discount is applied.

## Assumptions and boundaries

The group must confirm actual required fields, markup, minimum margin and approval rules. Prototype conventions are simulated data, AUD, a consistent quoted quantity and two-decimal prices. UC-08 owns campaign and approved member-offer rules; UC-07 determines eligibility. The base SupplierOffer assessment uses zero discount. Conditional customer quote validation follows A7 and reuses deterministic pricing; no extra service, payment integration or additional personal diagram set is required. Authentication, intake and delivery are supplied by UC-05; the Supplier component does not reimplement them.
