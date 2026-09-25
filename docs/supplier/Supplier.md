# Supplier final report copy and integration notes

## 1. Copy into Section 13 Complex Structure Diagram

### Supplier offer assessment runtime views

G-05A, G-05B and G-05C describe the Supplier Partnership contribution to the group runtime model. The scenario uses a simulated Sydney-to-Melbourne transport offer and the existing G-04 classifiers.

- G-05A is an object snapshot linking a traveller and membership context to a draft itinerary item, an approved SupplierOffer, its source evidence and PriceBreakdown. The base cost is AUD 180.00, markup is 10%, selling price is AUD 198.00 and margin is AUD 18.00. The minimum-margin fixture is AUD 15.00. The draft contains only the illustrated transport item; it is not presented as a complete feasible itinerary.
- G-05B is a communication diagram for the successful UC-06 assessment requiring human approval. Numbered messages show Operations requesting assessment, followed by extraction, deterministic validation and pricing, Reviewer review and the human decision. Failed checks and revision behaviour remain specified in UC-06 and SD-04. Operations retains external delivery responsibility.
- G-05C shows the internal structure of SupplierAssessmentContext. Typed parts reuse SupplierPartnershipAgent, LLMAdapter, ConstraintValidationService, PricingService and ReviewerGuardrail. Ports and connectors express the service contracts and delegation of intake and human-decision requests. This context is a runtime design refinement, not an additional business-domain entity or deployment.

The three views cover the supplier assessment collaboration. The group integrates the remaining planning, exception-handling and shared UI/persistence views. Local records and ordinary function calls are sufficient; no external advertising, payment system, background expiry service or message broker is required.

Insert G-05A_Object.png, G-05B_Communication.png and G-05C_Composite.png below the corresponding descriptions. Use separate landscape pages or full-width figures at a readable size. The editable file contains three pages.

## 2. Replace the Related diagrams field in SUP-AH-02 and UC-08

Related diagrams: G-03 (overall use-case coverage). AD-04, SD-04, SM-04 and G-05A/B/C describe the UC-06 supplier-offer assessment dependency; they do not directly model the UC-08 campaign approval workflow.

Do not change the SUP-AH-01 / UC-06 personal diagram links. Do not rename the personal diagram IDs.

## 3. Add the Supplier rows to the group traceability record

- SUP-01 and SUP-AH-01 -> UC-06 -> AD-04, SD-04, SM-04 -> G-04 SupplierOffer, Supplier, Evidence and SupplierCase -> G-05A/B/C -> UC-06 AC-01, AC-03 to AC-08 -> owner: Jason.
- SUP-02 and SUP-AH-01 -> UC-06 -> AD-04, SD-04, SM-04 (base assessment) -> G-04 PriceBreakdown, PricingService and IPricingService -> G-05A/B/C -> UC-06 AC-02 -> owner: Jason.
- Member-offer quote extension of SUP-02 -> UC-06 A7, UC-07 eligibility, approved UC-08 MemberOfferRule -> G-04 MemberOfferRule and PriceBreakdown -> UC-06 AC-09/AC-10. It is specified in text and the class model; the personal diagrams and G-05 views do not depict its full conditional flow.
- SUP-03 and SUP-AH-02 -> UC-08 -> G-03 and G-04 CampaignBrief, CampaignProposal, MemberOfferRule and HumanApproval -> UC-08 AC-UC08-01 to AC-UC08-10 -> owner: Jason. No standalone campaign behaviour diagram is claimed.
- SUP-O1 -> optional supplier reliability summary -> acceptance: calculate cancellations / eligible final outcomes; zero outcomes gives Not applicable; no unsupported prediction. No completed core behaviour diagram or implemented code is claimed for this optional feature.

These are requirement-to-model links and planned acceptance checks, not claims that Stage 2 code tests have passed. G-03 and G-02 require the group to confirm the final figure coverage.

## 4. Suggested contribution wording for review

Supplier Partnership materials include the SUP requirements, UC-06 and UC-08 specifications, AD-04/SD-04/SM-04, and the Supplier contribution to G-05A/B/C. The runtime views reuse the current G-04 class and operation names and document the Operations hand-off, price/margin validation and scoped human approval. Jason reviews and integrates these materials with the group. Contributions to G-02, G-03 and G-04, and each member's contribution percentage, must reflect the actual work agreed and performed by the team.

Only use this wording after you have reviewed and can explain the diagrams. Apply the course's actual rules for acknowledging tool assistance; no course-specific policy has been inferred here.

## 5. Align wording for customer-specific prices

Where the combined report says that UC-06 applies a discount to SupplierOffer, use this clearer sentence:

UC-06 calculates a separate customer-specific PriceBreakdown using the approved MemberOfferRule and UC-07 eligibility decision. It rechecks the final selling price and minimum margin without overwriting the reusable SupplierOffer base price. A failed discounted quotation does not invalidate an otherwise valid approved SupplierOffer.

## 6. Match the current optional-feature section number

The latest combined TripMate AI.md uses 4.3 for Supplier Partnership. The earlier supplier-only file labels it 4.4. Copy SUP-O1 into the current Supplier section and follow the combined report numbering; SUP-O1 itself stays unchanged.
