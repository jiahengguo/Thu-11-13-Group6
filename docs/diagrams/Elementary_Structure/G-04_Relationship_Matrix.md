> 2026-09-17 修订说明：本文保留为原候选设计/历史审计，其中 43 类、59 条关系和 Pass 结论不再代表当前版本。当前实图见 [Current Model](G-04_Current_Model.md)，重新核对结果见 [Course Compliance Audit](G-04_Course_Compliance_Audit.md)。

# G-04 Elementary Structure Modelling - Relationship Matrix

This matrix preserves the full candidate relationship catalogue considered during design. The optimised unlimited-canvas diagram renders the audited 59-relationship subset documented in `G-04_Optimization_Audit.md`. Former labels such as G-04A through G-04E are historical business-region labels and no longer refer to separate diagram pages.

## 1. Reading rules

- Every structural association, aggregation, and composition has multiplicity at both ends.
- Every connector has a visible direction marker. For a bidirectional association, arrowheads appear at both ends.
- Role names use lower camel case and are placed at the applicable association ends.
- Generalization points from child to parent.
- Realization points from implementing class to interface with a dashed line and hollow triangle.
- Dependency points from client to supplier with a dashed open arrow and `<<uses>>` where helpful.
- Composition/aggregation places the diamond at the whole end and a navigability arrow at the part end.

Multiplicity columns state how many instances at that end may be linked to one instance at the opposite end.

## 2. Master relationships

### 2.1 Generalization

| ID | Source | Target | Type and direction | Rationale | Source |
| --- | --- | --- | --- | --- | --- |
| GEN-01 | `OperationsAgent` | `Agent` | Generalization: child -> parent | Operations is one specialized Agent and inherits common handling, review, and trace responsibilities. | OPS-02/03 |
| GEN-02 | `TravelPlanningAgent` | `Agent` | Generalization: child -> parent | Travel Planning is a specialized Agent. | TP-01/02 |
| GEN-03 | `CustomerExceptionAgent` | `Agent` | Generalization: child -> parent | Customer Exception is a specialized Agent. | EXC-01/02 |
| GEN-04 | `SupplierPartnershipAgent` | `Agent` | Generalization: child -> parent | Supplier Partnership is a specialized Agent. | SUP-01/02/03 |
| GEN-05 | `CustomerCase` | `Case` | Generalization: child -> parent | A confirmed customer case is a Case with customer-specific type/risk data. | UC-05 |
| GEN-06 | `SupplierCase` | `Case` | Generalization: child -> parent | A confirmed supplier case is a Case with supplier-specific data. | UC-05/06 |

### 2.2 Intake, membership, and coordination associations

| ID | Source | Target | Type / navigability | Source multiplicity and role | Target multiplicity and role | Association name | Rationale |
| --- | --- | --- | --- | --- | --- | --- | --- |
| OPS-REL-01 | `Traveller` | `ExternalRequest` | Association, Traveller -> Request | `1 requester` | `0..* submittedRequests` | `submits` | A Traveller may submit many requests; a request has one requester. |
| OPS-REL-02 | `Supplier` | `ExternalRequest` | Association, Supplier -> Request | `1 requester` | `0..* submittedRequests` | `submits` | A Supplier may submit many requests; a supplier request has one requester. Constraint: exactly one of Traveller/Supplier is requester. |
| OPS-REL-03 | `ExternalRequest` | `Case` | Association, Request -> Case | `1 sourceRequest` | `0..* resultingCases` | `producesAfterConfirmation` | An unconfirmed request produces no Case; a multi-intent request may produce several Cases. Each Case has one source request. |
| OPS-REL-04 | `Case` | `CaseAssignment` | Association, Case -> Assignment | `1 assignedCase` | `0..* assignments` | `hasAssignmentHistory` | Assignment history survives routing changes. |
| OPS-REL-05 | `CaseAssignment` | `Agent` | Association, bidirectional | `0..* assignments` | `1 assignedAgent` | `assigns` | An assignment names exactly one Agent; an Agent has many assignments over time. |
| OPS-REL-06 | `Traveller` | `Subscription` | Association, Traveller -> Subscription | `1 subscriber` | `0..* subscriptionHistory` | `holds` | Paid entitlement depends on active subscription evidence; history is preserved. |
| OPS-REL-07 | `Subscription` | `MembershipPlan` | Association, Subscription -> Plan | `0..* subscriptions` | `1 subscribedPlan` | `appliesPlan` | Each subscription refers to one plan; a plan may be used by many subscriptions. |
| OPS-REL-08 | `Traveller` | `EntitlementDecision` | Association, Traveller -> Decision | `1 subject` | `0..* entitlementHistory` | `receives` | Decisions are immutable historical results for a Traveller. |
| OPS-REL-09 | `Case` | `EntitlementDecision` | Association, Case -> Decision | `1 relatedCase` | `0..* decisions` | `requires` | One Case can have initial and post-planning checks. |
| OPS-REL-10 | `ItineraryVersion` | `EntitlementDecision` | Association, Version -> Decision | `0..1 assessedVersion` | `0..* decisions` | `isAssessedBy` | Pre-planning decisions have no version; post-planning decisions reference one. |
| OPS-REL-11 | `OperationsAgent` | `ExternalRequest` | Association, Operations -> Request | `1 intakeAgent` | `0..* processedRequests` | `processes` | Operations owns intake and confirmation. |
| OPS-REL-12 | `OperationsAgent` | `CaseAssignment` | Association, Operations -> Assignment | `1 coordinator` | `0..* coordinatedAssignments` | `coordinates` | Operations records and tracks hand-offs. |

Constraint: `{ExternalRequest.requester is exactly one Traveller or one Supplier}`.

### 2.3 Travel, supplier, exception, and campaign structure

| ID | Source | Target | Type / navigability | Source multiplicity and role | Target multiplicity and role | Association name | Rationale |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PLAN-REL-01 | `Traveller` | `TravelPlan` | Association, bidirectional | `1 owner` | `0..* travelPlans` | `owns` | A plan belongs to one Traveller; a Traveller may hold many historical plans. UC-07 constrains simultaneous Planned/Active plans for Free Members. |
| PLAN-REL-02 | `CustomerCase` | `TravelPlan` | Association, Case -> Plan | `1 sourceCase` | `0..1 resultingPlan` | `createsOrRevises` | Not every CustomerCase is planning-related; a planning/revision Case affects at most one plan. |
| PLAN-REL-03 | `TravelPlan` | `ItineraryVersion` | Composition, black diamond at TravelPlan; TravelPlan -> Version | `1 plan` | `1..* versions {ordered, unique}` | `contains` | Versions have identity only within their plan and are preserved as an ordered immutable history. |
| PLAN-REL-04 | `ItineraryVersion` | `ItineraryVersion` | Directed self-association, successor -> baseline | `0..* successorVersions` | `0..1 previousVersion` | `revises` | Baseline has zero or more proposed successors; each revision has at most one direct baseline. |
| PLAN-REL-05 | `ItineraryVersion` | `ItineraryItem` | Composition, black diamond at Version; Version -> Item | `1 itineraryVersion` | `1..* items {ordered, unique}` | `comprises` | Item lifecycle and ordering belong to one immutable version. |
| PLAN-REL-06 | `ItineraryItem` | `SupplierOffer` | Association, Item -> Offer | `0..* itineraryItems` | `1 selectedOffer` | `selects` | Each item is justified by one selectable offer; an offer can be selected by many versions. |
| SUP-REL-01 | `Supplier` | `SupplierOffer` | Association, bidirectional | `1 offerOwner` | `0..* offers` | `provides` | Every offer has one Supplier; a Supplier may have many offers. |
| SUP-REL-02 | `SupplierOffer` | `TravelProduct` | Association, Offer -> Product | `0..* offers` | `1 offeredProduct` | `offers` | Product identity is independent of a time-bounded commercial offer. |
| SUP-REL-03 | `SupplierOffer` | `PriceBreakdown` | Composition, black diamond at Offer; Offer -> Breakdown | `1 pricedOffer` | `1..* priceBreakdowns {ordered}` | `ownsPricingHistory` | Base and customer-specific calculations cannot exist without their offer and must not overwrite history. |
| SUP-REL-04 | `SupplierCase` | `SupplierOffer` | Association, Case -> Offer | `1 sourceCase` | `0..1 assessedOffer` | `assesses` | A supplier offer intake case creates/updates at most one assessment target. |
| EXC-REL-01 | `CustomerCase` | `ExceptionCase` | Association, CustomerCase -> ExceptionCase | `1 sourceCustomerCase` | `0..1 exceptionHandling` | `opens` | Only disruption/complaint CustomerCases open an ExceptionCase. |
| EXC-REL-02 | `ExceptionCase` | `ExceptionIssue` | Composition, black diamond at ExceptionCase; ExceptionCase -> Issue | `1 investigation` | `1 investigatedIssue` | `investigates` | The specialist issue is the core content of exactly one ExceptionCase. |
| EXC-REL-03 | `ExceptionCase` | `RecoveryProposal` | Association, ExceptionCase -> Proposal | `1 recoveryCase` | `0..* recoveryProposals {ordered}` | `produces` | Revision history is retained after failed validation/review. |
| EXC-REL-04 | `ExceptionCase` | `ResolutionRecommendation` | Association, ExceptionCase -> Recommendation | `1 complaintCase` | `0..* recommendations {ordered}` | `produces` | Complaint recommendations retain revision history. |
| EXC-REL-05 | `RecoveryProposal` | `ItineraryVersion` | Association, Proposal -> Version | `0..* recoveryProposals` | `1 proposedVersion` | `proposes` | A recovery proposal describes one revised itinerary version. |
| CAM-REL-01 | `CampaignProposal` | `SupplierOffer` | Shared aggregation, white diamond at CampaignProposal; Proposal -> Offer | `0..* campaigns` | `1..* selectedOffers {unique}` | `aggregates` | Offers exist independently, can be reused, and are not deleted with a campaign. |
| CAM-REL-02 | `SupplierPartnershipAgent` | `CampaignProposal` | Association, Agent -> Proposal | `1 planningAgent` | `0..* proposals` | `prepares` | Supplier Partnership owns proposal preparation/evaluation coordination. |

### 2.4 Review, approval, and trace structure

| ID | Source | Target | Type / navigability | Source multiplicity and role | Target multiplicity and role | Association name | Rationale |
| --- | --- | --- | --- | --- | --- | --- | --- |
| GOV-REL-01 | `ReviewerGuardrail` | `ReviewResult` | Association, Reviewer -> Result | `1 reviewer` | `0..* reviewResults` | `creates` | Every review attempt creates an immutable result. |
| GOV-REL-02 | `HumanFounderOperator` | `HumanApproval` | Association, Operator -> Approval | `1 decisionMaker` | `0..* approvalHistory` | `decides` | Every human decision records its decision maker. |
| GOV-REL-03 | `Agent` | `AgentRun` | Association, Agent -> Run | `1 executingAgent` | `0..* runs` | `executes` | An Agent has many executions; each run belongs to one Agent. |
| GOV-REL-04 | `Case` | `AgentRun` | Association, Case -> Run | `0..1 relatedCase` | `0..* runs` | `isProcessedBy` | Campaign or maintenance runs may have no Case; case processing may require many Agent runs. |
| GOV-REL-05 | `AgentRun` | `TraceEntry` | Composition, black diamond at Run; Run -> Entry | `1 run` | `1..* entries {ordered}` | `records` | Trace entries have lifecycle and sequence within one run. |

## 3. Master dependencies on service interfaces

| ID | Client | Supplier interface | Type and direction | Reason |
| --- | --- | --- | --- | --- |
| DEP-01 | `Agent` | `ILLMService` | Dashed `<<uses>>`, Agent -> Interface | Shared extraction, drafting, and explanation capability. |
| DEP-02 | `Agent` | `ITraceRepository` | Dashed `<<uses>>`, Agent -> Interface | All Agents append auditable trace entries. |
| DEP-03 | `OperationsAgent` | `IEntitlementService` | Dashed `<<uses>>`, Operations -> Interface | Operations invokes deterministic entitlement decisions. |
| DEP-04 | `TravelPlanningAgent` | `IConstraintValidationService` | Dashed `<<uses>>`, Planning -> Interface | Feasibility and hard constraints are deterministic. |
| DEP-05 | `CustomerExceptionAgent` | `IConstraintValidationService` | Dashed `<<uses>>`, Exception -> Interface | Recovery proposals require deterministic validation. |
| DEP-06 | `SupplierPartnershipAgent` | `IConstraintValidationService` | Dashed `<<uses>>`, Supplier -> Interface | Offer and campaign consistency require deterministic validation. |
| DEP-07 | `SupplierPartnershipAgent` | `IPricingService` | Dashed `<<uses>>`, Supplier -> Interface | Price and margin calculations are deterministic. |
| DEP-08 | `TravelPlanningAgent` | `IReviewService` | Dashed `<<uses>>`, Planning -> Interface | Plan recommendation/comparison is reviewed. |
| DEP-09 | `CustomerExceptionAgent` | `IReviewService` | Dashed `<<uses>>`, Exception -> Interface | Recovery/resolution outputs are reviewed. |
| DEP-10 | `SupplierPartnershipAgent` | `IReviewService` | Dashed `<<uses>>`, Supplier -> Interface | Offers and campaigns are reviewed. |

## 4. Auxiliary generalizations and realizations

| ID | Source | Target | Type and direction | Diagram | Rationale |
| --- | --- | --- | --- | --- | --- |
| GEN-A01 | `TripLeg` | `ItineraryItem` | Generalization: child -> parent | G-04B | A TripLeg is one itinerary item type. |
| GEN-A02 | `AccommodationStay` | `ItineraryItem` | Generalization: child -> parent | G-04B | An AccommodationStay is one itinerary item type. |
| GEN-A03 | `ActivitySelection` | `ItineraryItem` | Generalization: child -> parent | G-04B | An ActivitySelection is one itinerary item type. |
| GEN-A04 | `TransportProduct` | `TravelProduct` | Generalization: child -> parent | G-04B | A TransportProduct is one travel product type. |
| GEN-A05 | `AccommodationProduct` | `TravelProduct` | Generalization: child -> parent | G-04B | An AccommodationProduct is one travel product type. |
| GEN-A06 | `ActivityProduct` | `TravelProduct` | Generalization: child -> parent | G-04B | An ActivityProduct is one travel product type. |
| GEN-A07 | `DisruptionEvent` | `ExceptionIssue` | Generalization: child -> parent | G-04C | A disruption is one investigated issue type. |
| GEN-A08 | `Complaint` | `ExceptionIssue` | Generalization: child -> parent | G-04C | A complaint is one investigated issue type. |
| REAL-01 | `LLMAdapter` | `ILLMService` | Realization: class - -|> interface | G-04E | Concrete LLM boundary implementation. |
| REAL-02 | `EntitlementService` | `IEntitlementService` | Realization | G-04A/E | Deterministic entitlement implementation. |
| REAL-03 | `ConstraintValidationService` | `IConstraintValidationService` | Realization | G-04E | Deterministic validation implementation. |
| REAL-04 | `PricingService` | `IPricingService` | Realization | G-04D/E | Deterministic price/margin implementation. |
| REAL-05 | `ReviewerGuardrail` | `IReviewService` | Realization | G-04E | Shared review implementation. |
| REAL-06 | `TraceRepository` | `ITraceRepository` | Realization | G-04E | Trace persistence implementation. |
| REAL-07 | `AccessControlService` | `IAccessControlService` | Realization | G-04A | Identity/access implementation. |

## 5. Auxiliary review and approval relationships

| ID | Source | Target | Type / navigability | Source multiplicity and role | Target multiplicity and role | Diagram / rationale |
| --- | --- | --- | --- | --- | --- | --- |
| REV-01 | `SupplierOffer` | `Reviewable` | Realization: Offer - -|> Interface | - | - | G-04D/E; offer approval requires Reviewer pass. |
| REV-02 | `ItineraryVersion` | `Reviewable` | Realization | - | - | G-04B/E; recommended plan must be reviewed. |
| REV-03 | `RecoveryProposal` | `Reviewable` | Realization | - | - | G-04C/E. |
| REV-04 | `ResolutionRecommendation` | `Reviewable` | Realization | - | - | G-04C/E. |
| REV-05 | `CampaignProposal` | `Reviewable` | Realization | - | - | G-04D/E. |
| APP-01 | `SupplierOffer` | `Approvable` | Realization | - | - | G-04D/E; restricted terms/binding prices may require approval. |
| APP-02 | `RecoveryProposal` | `Approvable` | Realization | - | - | G-04C/E; restricted recovery commitments require approval. |
| APP-03 | `ResolutionRecommendation` | `Approvable` | Realization | - | - | G-04C/E; refund/compensation recommendations require approval. |
| APP-04 | `CampaignProposal` | `Approvable` | Realization | - | - | G-04D/E; every campaign proposal requires approval. |
| REV-06 | `Reviewable` | `ReviewResult` | Association, Reviewable -> Result | `1 reviewedSubject` | `0..* reviewHistory {ordered}` | G-04E; every revision can create a fresh review result. |
| APP-05 | `Approvable` | `HumanApproval` | Association, Approvable -> Approval | `1 approvalSubject` | `0..* approvalHistory {ordered}` | G-04E; material revision creates a new decision rather than overwriting history. |
| EVD-01 | `ReviewResult` | `Evidence` | Association, ReviewResult -> Evidence | `0..* supportedReviews` | `1..* consideredEvidence {unique}` | G-04E; evidence is reusable and not owned by the review result. |
| POL-01 | `ReviewerGuardrail` | `Policy` | Association, Reviewer -> Policy | `0..* reviewers` | `1..* appliedPolicies` | G-04E; review records policy versions used. |
| POL-02 | `EntitlementService` | `Policy` | Association, Service -> Policy | `0..* services` | `1..* appliedPolicies` | G-04A/E. |
| POL-03 | `ConstraintValidationService` | `Policy` | Association, Service -> Policy | `0..* services` | `1..* appliedPolicies` | G-04E. |
| POL-04 | `PricingService` | `Policy` | Association, Service -> Policy | `0..* services` | `1..* appliedPolicies` | G-04D/E. |

## 6. Auxiliary domain relationships

### 6.1 Operations and Optional OPS-O1

| ID | Source | Target | Type / navigability | Source multiplicity and role | Target multiplicity and role | Association name |
| --- | --- | --- | --- | --- | --- | --- |
| OPS-A01 | `CampaignProposal` | `CampaignResponse` | Association, Campaign -> Response | `1 sourceCampaign` | `0..* responses` | `generatesInSimulation` |
| OPS-A02 | `CampaignResponse` | `ExternalRequest` | Association, Response -> Request | `0..1 campaignResponse` | `1 intakeRequest` | `entersOperationsAs` |
| OPS-A03 | `CampaignResponse` | `Lead` | Association, Response -> Lead | `1 sourceResponse` | `0..1 derivedLead` | `creates` |
| OPS-A04 | `Lead` | `Traveller` | Association, Lead -> Traveller | `0..1 convertedTraveller` | `0..* originatingLeads` | `convertsTo` |
| OPS-A05 | `AnalysisReport` | `CampaignMetric` | Aggregation, white diamond at Report; Report -> Metric | `0..* reports` | `1..* metrics {unique}` | `summarises` |

### 6.2 Travel planning

| ID | Source | Target | Type / navigability | Source multiplicity and role | Target multiplicity and role | Association name |
| --- | --- | --- | --- | --- | --- | --- |
| PLAN-A01 | `CustomerCase` | `TravelRequest` | Composition, black diamond at CustomerCase; Case -> Request | `1 planningCase` | `0..1 confirmedTravelRequest` | `captures` |
| PLAN-A02 | `TravelRequest` | `ConstraintSet` | Composition, black diamond at TravelRequest; Request -> Constraints | `1 travelRequest` | `1 confirmedConstraints` | `normalisesTo` |
| PLAN-A03 | `ItineraryVersion` | `ConstraintSet` | Association, Version -> Constraints | `0..* versions` | `1 appliedConstraints` | `satisfies` |
| PLAN-A04 | `PlanComparison` | `ItineraryVersion` | Association, Comparison -> Version | `0..* baselineComparisons` | `1 baseline` | `comparesBaseline` |
| PLAN-A05 | `PlanComparison` | `ItineraryVersion` | Association, Comparison -> Version | `0..* revisionComparisons` | `1 revision` | `comparesRevision` |
| PLAN-A06 | `ItineraryVersion` | `ValidationResult` | Association, Version -> Result | `1 validatedVersion` | `1..* validationHistory {ordered}` | `isValidatedBy` |
| PLAN-A07 | `IKnowledgeRetrievalService` | `GuidanceDocument` | Dependency/result, Interface -> Document | - | - | `retrieves` |

### 6.3 Customer exception and Optional EXC-O1

| ID | Source | Target | Type / navigability | Source multiplicity and role | Target multiplicity and role | Association name |
| --- | --- | --- | --- | --- | --- | --- |
| EXC-A01 | `ExceptionCase` | `Evidence` | Association, ExceptionCase -> Evidence | `0..* investigations` | `0..* collectedEvidence {unique}` | `collects` |
| EXC-A02 | `ExceptionIssue` | `ItineraryVersion` | Association, Issue -> Version | `0..* issues` | `1 affectedVersion` | `affects` |
| EXC-A03 | `ExternalUpdate` | `ItineraryVersion` | Association, Update -> Version | `0..* matchingUpdates` | `0..* potentiallyAffectedVersions` | `matches` |
| EXC-A04 | `ExternalUpdate` | `DisruptionNotification` | Association, Update -> Notification | `1 sourceUpdate` | `0..* proposedNotifications` | `supports` |
| EXC-A05 | `DisruptionNotification` | `Traveller` | Association, Notification -> Traveller | `0..* notifications` | `1 intendedRecipient` | `targets` |
| EXC-A06 | `ExceptionCase` | `HumanReferral` | Composition, black diamond at ExceptionCase; Case -> Referral | `1 referredCase` | `0..1 referral` | `createsWhenUnsafe` |

### 6.4 Supplier and campaign

| ID | Source | Target | Type / navigability | Source multiplicity and role | Target multiplicity and role | Association name |
| --- | --- | --- | --- | --- | --- | --- |
| SUP-A01 | `Supplier` | `SupplierAgreement` | Association, bidirectional | `1 agreementOwner` | `0..* agreements` | `enters` |
| SUP-A02 | `SupplierOffer` | `SupplierAgreement` | Association, Offer -> Agreement | `0..* governedOffers` | `0..1 governingAgreement` | `isGovernedBy` |
| SUP-A03 | `SupplierOffer` | `Evidence` | Association, Offer -> Evidence | `0..* supportedOffers` | `1..* sourceEvidence {unique}` | `isSupportedBy` |
| CAM-A01 | `HumanFounderOperator` | `CampaignBrief` | Association, Operator -> Brief | `1 briefOwner` | `0..* briefs` | `submits` |
| CAM-A02 | `CampaignBrief` | `CampaignProposal` | Association, Brief -> Proposal | `1 sourceBrief` | `1..* proposalVersions {ordered}` | `drives` |
| CAM-A03 | `CampaignProposal` | `CampaignCostItem` | Composition, black diamond at Proposal; Proposal -> CostItem | `1 campaignProposal` | `1..* costItems` | `estimatesWith` |
| CAM-A04 | `CampaignProposal` | `MemberOfferRule` | Composition, black diamond at Proposal; Proposal -> Rule | `1 campaignProposal` | `0..1 memberOfferRule` | `defines` |
| CAM-A05 | `MemberOfferRule` | `SupplierOffer` | Association, Rule -> Offer | `0..* memberOfferRules` | `1..* applicableOffers {unique}` | `appliesTo` |
| SUP-A04 | `SupplierReliabilitySummary` | `Supplier` | Association, Summary -> Supplier | `0..* summaries` | `1 assessedSupplier` | `summarises` |

## 7. Constraint notes for the Master

The Master carries only these high-value constraint notes:

1. `{ItineraryVersion is immutable; a confirmed amendment creates a successor and never overwrites the baseline}`
2. `{Only Approved and unexpired SupplierOffers may be selected}`
3. `{sellingPrice.amount > 0 and marginAmount >= configuredMinimumMargin}`
4. `{Restricted financial, contractual, legal, safety, access, publication, refund, and compensation decisions require HumanApproval}`
5. `{Free tier: Planned/Active TravelPlans <= 2 and inclusive trip duration <= 5 calendar days}`
6. `{at most one active PRIMARY_HANDLER per Case}`

## 8. Layout-specific connector rules

1. Use orthogonal/elbow connectors only.
2. No connector may overlap another connector, a class border, class text, role name, multiplicity, arrowhead, or diamond.
3. Target zero crossings. Where a crossing cannot be eliminated without changing semantics, use a visible line jump.
4. Keep diamonds clear of multiplicity labels.
5. Keep inheritance children aligned beneath or beside a centered parent; do not merge unrelated generalization trunks.
6. A line may not be rerouted in a way that changes its source, target, diamond end, or arrow direction from this matrix.
7. Every selected classifier appears exactly once in the single submission diagram.
