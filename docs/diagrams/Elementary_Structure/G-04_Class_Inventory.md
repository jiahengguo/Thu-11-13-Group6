> 2026-09-17 修订说明：本文保留为原候选设计/历史审计，其中 43 类、59 条关系和 Pass 结论不再代表当前版本。当前实图见 [Current Model](G-04_Current_Model.md)，重新核对结果见 [Course Compliance Audit](G-04_Course_Compliance_Audit.md)。

# G-04 Elementary Structure Modelling - Class Inventory

## 1. Purpose and authority

This inventory is the design specification for the TripMate AI Elementary Structure Models.

Source priority:

1. `docs/TripMate AI.md` - authoritative functional and domain baseline.
2. `docs/ELEC5620_Project_Stage_1_Marking_Criteria.pdf` - assessment requirements.
3. ELEC5620 Week 6 lecture, tutorial, and laboratory - UML class-diagram notation.
4. ELEC5620 Week 7 materials - consistency with later runtime object and collaboration models.
5. Existing activity, interaction, and state-machine diagrams - cross-model operation and lifecycle checks.

The SharePoint copy is reference-only and does not override the local Markdown baseline.

## 2. Diagram allocation

| Code | Meaning |
| --- | --- |
| M | Core cross-domain classifier in the complete diagram. |
| A | Detailed supporting classifier in the same complete diagram. |
| O | Supports a selected Optional Feature and remains in the same complete diagram. |

The allocation codes record the complete candidate inventory considered during design. The optimised submission diagram applies an additional major-class filter and includes 43 selected classifiers on one large canvas. Excluded candidates remain documented here so that future sequence/state evidence can justify restoration without inventing new terminology.

Member notation for draw.io:

- Attributes are private by default and use `-name: Type`.
- Public business operations use `+operation(parameter: Type): ReturnType`.
- Protected members are used only when subclasses genuinely inherit/override them.
- Derived properties use a leading slash, for example `/durationInDays: Integer`.
- Constructors, getters, and setters are omitted.
- Abstract class names are italicized and also marked `<<abstract>>` where space permits.

## 3. Core classifier set

The core inventory contains 38 cross-domain candidates. After the course-driven optimisation audit, the final submission diagram contains 43 major classifiers and 59 relationships. DataTypes and Enumerations remain visible as typed member vocabulary, while the six constraints are written inside their owning classifiers. The canvas is intentionally not constrained to one Word page so that classifiers, members, labels, multiplicities, and independent connector routes remain legible.

### 3.1 External roles and membership

| Classifier | Allocation | Responsibility | Key attributes | Key operations | Source |
| --- | --- | --- | --- | --- | --- |
| `Traveller` | M, A | Authenticated customer who submits and confirms requests and owns plans. | `travellerId: String`; `displayName: String`; `humanRequestCount: Integer` | `submitRequest(content: String): ExternalRequest`; `confirmRequest(requestId: String): void`; `confirmAmendment(amendment: String): void` | OPS-02, OPS-03, UC-01-05, UC-07 |
| `Supplier` | M, A | Travel Service Provider whose products, agreements, and offers enter through Operations. | `supplierId: String`; `name: String`; `eligibilityStatus: SupplierStatus` | `submitOffer(source: Evidence): ExternalRequest`; `provideCorrection(offerId: String): ExternalRequest` | SUP-01, UC-05, UC-06 |
| `HumanFounderOperator` | M, A | Human supervisor who makes restricted decisions and supplies campaign briefs. | `operatorId: String`; `authorityScope: String[*]` | `decide(subject: Approvable, decision: ApprovalDecision): HumanApproval`; `submitCampaignBrief(brief: CampaignBrief): CampaignProposal`; `takeOver(case: Case): void` | Sections 2.6, 3.6; UC-03-06, UC-08 |
| `MembershipPlan` | M, A | Defines a membership tier and its feature/advertising rules. | `planId: String`; `tier: MembershipTier`; `featureEntitlements: String[*]` | `allowsFeature(featureId: String): Boolean` | OPS-03, UC-07 |
| `Subscription` | M, A | Time-bounded evidence that a Traveller has an active paid plan. | `subscriptionId: String`; `status: SubscriptionStatus`; `validityPeriod: DateRange` | `isActive(on: Date): Boolean` | OPS-03, UC-07 |
| `EntitlementDecision` | M, A | Immutable result of a deterministic entitlement evaluation. | `decisionId: String`; `outcome: EntitlementOutcome`; `reason: String`; `decidedAt: DateTime` | `explainsFailure(): String` | OPS-03, UC-07 |

### 3.2 Intake and case coordination

| Classifier | Allocation | Responsibility | Key attributes | Key operations | Source |
| --- | --- | --- | --- | --- | --- |
| `ExternalRequest` | M, A | Stores the incoming content, extracted intents, missing fields, confidence, and confirmation before formal Case creation. | `requestId: String`; `sourceChannel: SourceChannel`; `classificationConfidence: Decimal`; `confirmed: Boolean` | `classify(): RequestClassification`; `identifyMissingFields(): String[*]`; `confirm(): void`; `createCasesAfterConfirmation(): Case[*]` | OPS-02, OPS-AH-01, UC-05 |
| `Case` | M, A | Abstract lifecycle root for confirmed coordinated work. | `caseId: String`; `status: CaseStatus`; `createdAt: DateTime`; `confirmedAt: DateTime` | `close(reason: ClosureReason): void`; `escalate(reason: String): void` | UC-05 |
| `CustomerCase` | M, A | Confirmed Traveller case for planning, revision, disruption, complaint, membership, or routine enquiry. | `caseType: CustomerCaseType`; `riskLevel: RiskLevel` | `requestClarification(question: String): void` | OPS-02, UC-01-05, UC-07 |
| `SupplierCase` | M, A | Confirmed supplier cooperation, inventory, offer, or pricing case. | `caseType: SupplierCaseType`; `supplierReference: String` | `requestSupplierCorrection(reason: String): void` | OPS-02, SUP-01, UC-05, UC-06 |
| `CaseAssignment` | M, A | Preserves coordinator, primary-handler, and supporting-agent assignments and hand-off history. | `role: AssignmentRole`; `assignedAt: DateTime`; `releasedAt: DateTime [0..1]`; `status: AssignmentStatus` | `assign(): void`; `release(): void` | UC-05, UC-03, UC-04 |

Constraint: `{at most one active PRIMARY_HANDLER per Case}`.

### 3.3 Agent hierarchy

| Classifier | Allocation | Responsibility | Key attributes | Key operations | Source |
| --- | --- | --- | --- | --- | --- |
| `Agent` | M, A | Abstract root containing behaviour shared by all four business Agents. | `agentId: String`; `status: AgentStatus` | `handleCase(case: Case): AgentResult`; `requestReview(subject: Reviewable): ReviewResult`; `recordTrace(entry: TraceEntry): void` | Sections 2.2-2.5; Week 6 Agent abstraction |
| `OperationsAgent` | M, A | Controlled external gateway, intake coordinator, router, response reviewer, and delivery owner. | `routingRulesVersion: String`; `requiredFieldRulesVersion: String` | `intake(request: ExternalRequest): Case[*]`; `route(case: Case): CaseAssignment`; `releaseResponse(case: Case): void` | OPS-02, OPS-03, UC-05, UC-07 |
| `TravelPlanningAgent` | M, A | Builds, validates, ranks, compares, and revises complete itinerary versions. | `defaultRankingMode: RankingMode` | `createPlan(request: TravelRequest): TravelPlan`; `createRevision(baseline: ItineraryVersion, amendment: String): ItineraryVersion`; `compareVersions(baseline: ItineraryVersion, revision: ItineraryVersion): PlanComparison` | TP-01, TP-02, UC-01, UC-02 |
| `CustomerExceptionAgent` | M, A | Investigates disruptions and complaints and prepares reviewed recovery or resolution outputs. | `confidenceThreshold: Decimal` | `investigate(issue: ExceptionIssue): ExceptionCase`; `prepareRecovery(case: ExceptionCase): RecoveryProposal`; `recommendResolution(case: ExceptionCase): ResolutionRecommendation` | EXC-01, EXC-02, UC-03, UC-04 |
| `SupplierPartnershipAgent` | M, A | Assesses offers, validates price/margin, and prepares supplier-data-based campaigns. | `pricingConfigVersion: String` | `assessOffer(case: SupplierCase, evidence: Evidence[*]): SupplierOffer`; `prepareCampaign(brief: CampaignBrief): CampaignProposal`; `summariseReliability(supplier: Supplier, period: DateRange): SupplierReliabilitySummary` | SUP-01-03, SUP-O1, UC-06, UC-08 |

### 3.4 Travel planning and supplier core

| Classifier | Allocation | Responsibility | Key attributes | Key operations | Source |
| --- | --- | --- | --- | --- | --- |
| `TravelPlan` | M, A | Stable plan aggregate owned by a Traveller and containing immutable itinerary versions. | `planId: String`; `status: PlanStatus`; `travelDates: DateRange` | `currentVersion(): ItineraryVersion`; `addVersion(version: ItineraryVersion): void` | TP-01, TP-02, UC-01, UC-02 |
| `ItineraryVersion` | M, A | Immutable feasible or draft version of an itinerary. | `versionId: String`; `versionNo: Integer`; `status: PlanStatus`; `rankingMode: RankingMode`; `totalPrice: Money` | `calculateDuration(): Integer`; `compareTo(other: ItineraryVersion): PlanComparison` | TP-01, TP-02, UC-01, UC-02, SM-02 |
| `ItineraryItem` | M, A | Abstract item selected into a version. | `itemId: String`; `startAt: DateTime`; `endAt: DateTime`; `quotedPrice: Money` | `validateTiming(): ValidationResult` | TP-01, UC-01 |
| `TravelProduct` | M, A | Abstract supplier product independent of a particular commercial offer. | `productId: String`; `name: String`; `productType: ProductType` | `describe(): String` | TP-01, SUP-01, UC-01, UC-06 |
| `SupplierOffer` | M, A | Timestamped supplier commercial offer with inventory, validity, terms, status, and evidence. | `offerId: String`; `status: OfferStatus`; `availableQuantity: Integer`; `validUntil: DateTime`; `supplierCost: Money` | `isSelectable(at: DateTime): Boolean`; `expire(): void`; `clearPriorDecisions(): void` | SUP-01, SUP-02, UC-01, UC-06, UC-08, SM-04 |
| `PriceBreakdown` | M, A | Immutable base or customer-specific price/margin calculation for one offer. | `supplierCost: Money`; `markupRate: Decimal`; `basePrice: Money`; `discountAmount: Money`; `sellingPrice: Money`; `marginAmount: Money` | `passesMinimumMargin(minimum: Money): Boolean` | SUP-02, UC-06 |

Constraints:

- `{ItineraryVersion is immutable}`
- `{Only Approved and unexpired SupplierOffers may be selected}`
- `{sellingPrice.amount > 0 and marginAmount >= configuredMinimumMargin}`

### 3.5 Exception and campaign core

| Classifier | Allocation | Responsibility | Key attributes | Key operations | Source |
| --- | --- | --- | --- | --- | --- |
| `ExceptionCase` | M, A | Specialist investigation record associated with a CustomerCase. | `exceptionCaseId: String`; `status: ExceptionStatus`; `confidence: Decimal` | `recordFinding(finding: String): void`; `referToHuman(reason: String): void` | EXC-01, EXC-02, UC-03, UC-04, SM-03 |
| `ExceptionIssue` | M, A | Abstract reported or detected issue investigated by an ExceptionCase. | `issueId: String`; `reportedAt: DateTime`; `severity: Severity`; `description: String` | `affectedItems(): ItineraryItem[*]` | EXC-01, EXC-02 |
| `RecoveryProposal` | M, A | Proposed changes for a disrupted active itinerary. | `proposalId: String`; `status: ProposalStatus`; `budgetImpact: Money`; `timingImpact: String` | `validate(): ValidationResult`; `revise(reasons: String[*]): RecoveryProposal` | EXC-01, UC-03 |
| `ResolutionRecommendation` | M, A | Evidence-supported complaint resolution or referral recommendation. | `recommendationId: String`; `status: ProposalStatus`; `recommendedResponse: String`; `restrictedCommitment: Boolean` | `validate(): ValidationResult`; `revise(reasons: String[*]): ResolutionRecommendation` | EXC-02, UC-04 |
| `CampaignProposal` | M, A | Supplier-data-based campaign proposal from brief through evaluation, review, and approval. | `campaignId: String`; `status: CampaignStatus`; `targetAudience: String`; `channel: SourceChannel`; `campaignDates: DateRange`; `budgetCeiling: Money` | `calculateEstimatedCost(): Money`; `invalidateApproval(): void`; `isEligibleForSimulation(): Boolean` | SUP-03, UC-08 |

### 3.6 Governance and audit

| Classifier | Allocation | Responsibility | Key attributes | Key operations | Source |
| --- | --- | --- | --- | --- | --- |
| `ReviewerGuardrail` | M, A | Implements shared evidence, calculation, constraint, policy, and approval-boundary review. | `reviewerId: String`; `policyVersion: String` | `review(subject: Reviewable, evidence: Evidence[*]): ReviewResult` | Section 2.7; all specialist UCs |
| `ReviewResult` | M, A | Immutable historical result of one review attempt. | `reviewId: String`; `outcome: ReviewOutcome`; `reasons: String[*]`; `reviewedAt: DateTime`; `approvalRequired: Boolean` | `passed(): Boolean` | Reviewer/Guardrail requirements |
| `HumanApproval` | M, A | Immutable scoped human decision; later revisions create new records. | `approvalId: String`; `decision: ApprovalDecision`; `reason: String`; `scope: String`; `decidedAt: DateTime` | `permits(subject: Approvable): Boolean` | Section 2.6; UC-03, UC-04, UC-06, UC-08 |
| `AgentRun` | M, A | One identifiable Agent execution associated with zero or one Case. | `runId: String`; `startedAt: DateTime`; `completedAt: DateTime [0..1]`; `status: RunStatus` | `start(): void`; `finish(status: RunStatus): void` | Agent Trace requirements; Week 6 Agent example |
| `TraceEntry` | M, A | Passive timestamped audit entry within an AgentRun. | `timestamp: DateTime`; `eventType: TraceEventType`; `subjectType: String`; `subjectId: String`; `summary: String` | - | Agent Trace requirements |

Constraint: `{Restricted financial, contractual, legal, safety, access, publication, refund, and compensation decisions require HumanApproval}`.

### 3.7 Core interfaces

| Interface | Allocation | Declared operations | Main users / implementation | Source |
| --- | --- | --- | --- | --- |
| `ILLMService` | M, A | `extract(input: String, schema: String): ExtractionResult`; `draft(context: String): String`; `explain(result: String): String` | All Agents / `LLMAdapter` | All Agent feature descriptions |
| `IEntitlementService` | M, A | `evaluate(traveller: Traveller, action: RequestedAction, dates: DateRange [0..1]): EntitlementDecision` | OperationsAgent / `EntitlementService` | OPS-03, UC-07 |
| `IConstraintValidationService` | M, A | `validatePlan(version: ItineraryVersion): ValidationResult`; `validateProposal(subject: Reviewable): ValidationResult` | Planning, Exception, Supplier Agents / `ConstraintValidationService` | TP-01/02, EXC-01/02, SUP-01/03 |
| `IPricingService` | M, A | `calculate(offer: SupplierOffer, discount: Money): PriceBreakdown`; `checkMargin(breakdown: PriceBreakdown): Boolean` | SupplierPartnershipAgent / `PricingService` | SUP-02, UC-06 |
| `IReviewService` | M, A | `review(subject: Reviewable, evidence: Evidence[*], policies: Policy[*]): ReviewResult` | Specialist Agents / `ReviewerGuardrail` | Section 2.7 |
| `ITraceRepository` | M, A | `append(run: AgentRun, entry: TraceEntry): void`; `findBySubject(type: String, id: String): TraceEntry[*]` | Agent / `TraceRepository` | Agent Trace requirements |

## 4. Supporting classifier candidates evaluated during optimisation

This section is the traceable candidate catalogue, not a statement that every row appears in the final diagram. The inclusion/exclusion decision for each category is recorded in `G-04_Optimization_Audit.md`.

### 4.1 Operations & Membership region

| Classifier | Allocation | Responsibility | Key attributes | Key operations | Source |
| --- | --- | --- | --- | --- | --- |
| `EntitlementService` | A | Deterministic implementation of `IEntitlementService`. | `ruleVersion: String` | `evaluate(...): EntitlementDecision` | OPS-03, UC-07 |
| `IAccessControlService` | A | Identity/access boundary used before protected processing. | - | `verifyIdentity(requesterId: String): AccessDecision`; `authorise(action: RequestedAction): AccessDecision` | UC-05, UC-07 |
| `AccessControlService` | A | Implements configured authentication and authorisation checks. | `policyVersion: String` | `verifyIdentity(...): AccessDecision`; `authorise(...): AccessDecision` | UC-05, UC-07 |
| `CampaignResponse` | A | Source-tagged response from an approved simulated campaign. | `responseId: String`; `campaignId: String`; `sourceChannel: SourceChannel`; `content: String`; `receivedAt: DateTime` | `toExternalRequest(): ExternalRequest` | OPS-02, UC-05, UC-08 A7 |
| `Lead` | A, O | Source-tagged acquisition lead derived from a CampaignResponse. | `leadId: String`; `createdAt: DateTime`; `consentStatus: ConsentStatus`; `qualificationStatus: QualificationStatus` | `qualify(rule: String): void`; `convert(traveller: Traveller): void` | OPS-O1 |
| `CampaignMetric` | A, O | Recorded numerator/denominator inputs and derived acquisition/retention measures. | `metricType: MetricType`; `period: DateRange`; `numerator: Decimal`; `denominator: Decimal`; `value: Decimal [0..1]` | `calculate(): Decimal [0..1]` | OPS-O1 |
| `AnalysisReport` | A, O | Evidence-based explanation of campaign, lead, membership, or retention metrics for human review. | `reportId: String`; `period: DateRange`; `assumptions: String[*]`; `limitations: String[*]` | `summarise(metrics: CampaignMetric[*]): String`; `recommendNextAction(): String` | OPS-O1, OPS-O2 |

### 4.2 Travel Planning region

| Classifier | Allocation | Responsibility | Key attributes | Key operations | Source |
| --- | --- | --- | --- | --- | --- |
| `TravelRequest` | A | Confirmed normalized planning input derived from a CustomerCase. | `requestId: String`; `origin: String`; `destination: String`; `partySize: Integer`; `budgetCeiling: Money`; `travelDates: DateRange`; `rankingMode: RankingMode` | `validateCompleteness(): ValidationResult`; `toConstraintSet(): ConstraintSet` | TP-01, TP-AH-01, UC-01 |
| `ConstraintSet` | A | Versioned hard and soft planning constraints. | `constraintSetId: String`; `hardConstraints: Constraint[*]`; `preferences: Preference[*]` | `conflictsWith(other: ConstraintSet): String[*]`; `changedFields(other: ConstraintSet): String[*]` | TP-01, TP-02 |
| `TripLeg` | A | Transport item in an itinerary version. | `origin: String`; `destination: String`; `departureAt: DateTime`; `arrivalAt: DateTime`; `transferCount: Integer` | `validateConnection(next: TripLeg): ValidationResult` | TP-01 |
| `AccommodationStay` | A | Accommodation item in an itinerary version. | `checkIn: DateTime`; `checkOut: DateTime`; `accessible: Boolean` | `validateStay(): ValidationResult` | TP-01 |
| `ActivitySelection` | A | Activity item in an itinerary version. | `activityDate: DateTime`; `openingHours: String`; `accessible: Boolean` | `validateOpeningHours(): ValidationResult` | TP-01 |
| `TransportProduct` | A | Transport specialization of `TravelProduct`. | `baggageAllowance: String`; `accessibilityInfo: String` | `supportsBaggage(requirement: String): Boolean` | TP-01 |
| `AccommodationProduct` | A | Accommodation specialization of `TravelProduct`. | `roomType: String`; `cancellationTerms: String` | `supportsAccessibility(): Boolean` | TP-01 |
| `ActivityProduct` | A | Activity specialization of `TravelProduct`. | `location: String`; `openingHours: String` | `isOpen(at: DateTime): Boolean` | TP-01 |
| `PlanComparison` | A | Field-level comparison between a baseline and revision. | `changedFields: String[*]`; `priceDelta: Money`; `tradeOffs: String[*]`; `assumptions: String[*]` | `renderExplanation(): String` | TP-02, UC-02 |
| `ValidationResult` | A | Deterministic validation result used before ranking or approval. | `passed: Boolean`; `failedRules: String[*]`; `calculatedAt: DateTime` | `requirePass(): void` | TP-01/02, EXC, SUP |
| `GuidanceDocument` | A, O | Cited destination or travel-policy guidance distinct from live availability. | `documentId: String`; `sourceUri: String`; `retrievedAt: DateTime`; `contentSummary: String` | `isFresh(at: DateTime): Boolean` | TP-O1 |
| `IKnowledgeRetrievalService` | A, O | Retrieves cited guidance documents. | - | `retrieve(query: String): GuidanceDocument[*]` | TP-O1 |

### 4.3 Customer Exception region

| Classifier | Allocation | Responsibility | Key attributes | Key operations | Source |
| --- | --- | --- | --- | --- | --- |
| `DisruptionEvent` | A | Disruption affecting one or more active itinerary items. | `eventType: DisruptionType`; `occurredAt: DateTime`; `confirmed: Boolean` | `assessImpact(version: ItineraryVersion): ItineraryItem[*]` | EXC-01, UC-03 |
| `Complaint` | A | Traveller-reported issue requiring evidence-supported investigation. | `category: ComplaintCategory`; `reportedAt: DateTime`; `statement: String` | `identifyIssue(): String` | EXC-02, UC-04 |
| `ExternalUpdate` | A, O | Simulated travel/weather update used for proactive disruption matching. | `updateId: String`; `provider: String`; `retrievedAt: DateTime`; `content: String`; `confirmed: Boolean` | `matches(version: ItineraryVersion): ItineraryItem[*]` | EXC-O1 |
| `DisruptionNotification` | A, O | Reviewed proposed notification explaining risk, affected items, source, and uncertainty. | `notificationId: String`; `status: NotificationStatus`; `possibleImpact: String`; `uncertainty: String` | `prepare(update: ExternalUpdate): void`; `markDelivered(): void` | EXC-O1 |
| `HumanReferral` | A | Documented referral when automated investigation cannot safely continue. | `referralId: String`; `reason: String`; `unresolvedIssues: String[*]`; `createdAt: DateTime` | `submit(operator: HumanFounderOperator): void` | UC-03, UC-04 |

### 4.4 Supplier & Campaign region

| Classifier | Allocation | Responsibility | Key attributes | Key operations | Source |
| --- | --- | --- | --- | --- | --- |
| `SupplierAgreement` | A | Supplier eligibility and permitted commercial terms used by validation. | `agreementId: String`; `status: AgreementStatus`; `validityPeriod: DateRange`; `permittedTerms: String[*]` | `isValid(at: Date): Boolean` | SUP-01, SUP-02 |
| `PricingService` | A | Deterministic implementation of `IPricingService`. | `configVersion: String`; `minimumMargin: Money` | `calculate(...): PriceBreakdown`; `checkMargin(...): Boolean` | SUP-02, UC-06 |
| `CampaignBrief` | A | Human-confirmed campaign objective, audience, channel, dates, budget, and restrictions. | `briefId: String`; `objective: String`; `audience: String`; `channel: SourceChannel`; `dates: DateRange`; `budgetCeiling: Money`; `restrictions: String[*]` | `validateCompleteness(): ValidationResult` | SUP-03, UC-08 |
| `CampaignCostItem` | A | One simulated cost basis item in a proposal estimate. | `description: String`; `plannedUnits: Decimal`; `unitCost: Money`; `fixedCost: Money` | `subtotal(): Money` | SUP-03, UC-08 |
| `MemberOfferRule` | A | Approved fixed-discount rule later checked by UC-07 and applied by UC-06. | `ruleId: String`; `eligibleTiers: MembershipTier[*]`; `discountAmount: Money`; `validityPeriod: DateRange` | `isApplicable(offer: SupplierOffer, tier: MembershipTier): Boolean` | SUP-03, UC-06, UC-07, UC-08 |
| `SupplierReliabilitySummary` | A, O | Deterministic completed-outcome and supplier-cancellation summary for a stated period. | `summaryId: String`; `period: DateRange`; `eligibleOutcomes: Integer`; `supplierCancellations: Integer`; `cancellationRate: Decimal [0..1]` | `calculateRate(): Decimal [0..1]`; `explainLimitations(): String` | SUP-O1 |

### 4.5 Shared Agent Control & Audit region

| Classifier | Allocation | Responsibility | Key attributes | Key operations | Source |
| --- | --- | --- | --- | --- | --- |
| `Reviewable` | A | Interface implemented by artefacts that must pass Reviewer/Guardrail checks. | - | `reviewIdentity(): String`; `materialVersion(): String` | Shared review rules |
| `Approvable` | A | Interface implemented by artefacts capable of requiring scoped Human Approval. | - | `approvalIdentity(): String`; `approvalScope(): String` | Shared approval rules |
| `Evidence` | A | Independent source/freshness/reliability record reusable across investigations and reviews. | `evidenceId: String`; `sourceUri: String`; `retrievedAt: DateTime`; `freshnessStatus: FreshnessStatus`; `reliability: ReliabilityLevel` | `isFresh(at: DateTime): Boolean` | All UCs |
| `Policy` | A | Versioned rule/policy reference used by deterministic services and Reviewer/Guardrail. | `policyId: String`; `name: String`; `version: String`; `effectiveFrom: Date`; `effectiveTo: Date [0..1]` | `isEffective(on: Date): Boolean` | OPS, TP, EXC, SUP rules |
| `LLMAdapter` | A | Concrete implementation of `ILLMService`; never the source of deterministic truth. | `modelReference: String` | `extract(...): ExtractionResult`; `draft(...): String`; `explain(...): String` | All Agent descriptions |
| `ConstraintValidationService` | A | Concrete deterministic implementation of validation rules. | `ruleSetVersion: String` | `validatePlan(...): ValidationResult`; `validateProposal(...): ValidationResult` | TP, EXC, SUP requirements |
| `TraceRepository` | A | Concrete persistence implementation of `ITraceRepository`. | `repositoryId: String` | `append(...): void`; `findBySubject(...): TraceEntry[*]` | Agent Trace requirements |

## 5. DataTypes

| DataType | Members | Notes |
| --- | --- | --- |
| `Money` | `amount: Decimal`; `currency: CurrencyCode` | Prototype rule: pricing calculations use AUD, but the type retains currency explicitly. |
| `DateRange` | `startDate: Date`; `endDate: Date`; `durationInDays(): Integer` | Duration is inclusive where the applicable rule states `endDate - startDate + 1`. |

## 6. Enumerations

The following eight core enumerations remain typed vocabulary in the final diagram rather than separate boxes. Secondary enumerations are defined in the glossary.

| Enumeration | Core literals |
| --- | --- |
| `CaseStatus` | `CONFIRMED`, `ROUTED`, `AWAITING_REQUESTER`, `AWAITING_HUMAN_APPROVAL`, `READY_TO_RESPOND`, `CLOSED`, `WITHDRAWN` |
| `OfferStatus` | `DRAFT`, `REVISION_REQUIRED`, `UNDER_REVIEW`, `AWAITING_APPROVAL`, `APPROVED`, `REJECTED`, `EXPIRED` |
| `PlanStatus` | `DRAFT`, `VALIDATING`, `FEASIBLE`, `REVIEWED`, `PLANNED`, `ACTIVE`, `COMPLETED`, `INFEASIBLE` |
| `MembershipTier` | `FREE`, `PAID` |
| `EntitlementOutcome` | `ALLOWED`, `DENIED`, `VERIFICATION_FAILED` |
| `ReviewOutcome` | `PASS`, `REVISION_REQUIRED` |
| `ApprovalDecision` | `APPROVE`, `REQUEST_REVISION`, `REJECT` |
| `RankingMode` | `COMFORT`, `VALUE`, `BUDGET` |

## 7. Deliberate exclusions

These are not omissions from the requirements; they are excluded to prevent the Class Diagram from becoming an implementation/database diagram.

| Excluded element | Treatment and reason |
| --- | --- |
| UI pages, forms, and screens | Behaviour belongs to the controlled interface but no page-level design is required in G-04. |
| Database tables and schemas | Domain classes and repository interfaces are modeled instead. |
| A separate repository class for every aggregate | Would add repetitive CRUD structure. Only the trace repository is explicit because audit behaviour is central. |
| REST endpoints and concrete external APIs | Outside the base prototype; service interfaces capture required boundaries. |
| Payment, booking, refund, compensation execution | Explicitly outside the prototype. Approval records do not execute transactions. |
| Real campaign publication and spending | UC-08 ends at approved proposal or optional simulation. |
| Background expiry/monitoring scheduler | UC-06 checks expiry on read; no scheduler is required. |
| Concrete runtime instances | Reserved for G-05 Object/Collaboration/Structured Class models. |
| `FreeTraveller` and `PaidTraveller` subclasses | Membership changes over time; use `Subscription` and `MembershipTier`, not inheritance. |
| A separate `AgentTrace` aggregate | `AgentRun` composed of `TraceEntry` provides the required auditable execution structure. |

## 8. Open verification items before drawing

1. **Case-creation timing conflict:** Sections 3.2 and 5.1 say a `CustomerCase`/`SupplierCase` is created after requester confirmation, while UC-05 Main Success Scenario step 3 creates a Draft Case before identity and confirmation. The confirmed G-04 design follows the first rule: `ExternalRequest` exists before confirmation and produces Case(s) after confirmation. UC-05 should be reconciled before submission.
2. SD-01, SD-02, SD-03 and their final message names are not currently present as editable files in the repository. Their major messages must be checked against the operations above when those diagrams become available.
3. SM-01, SM-02 and SM-03 must be checked against the final `CaseStatus`, `PlanStatus`, and `ExceptionStatus` literals before drawing is signed off.
4. The optimised large-canvas model contains 43 major classifiers. For a Word submission, use the SVG or a high-resolution PNG and a large landscape/fold-out page rather than splitting the model or forcing it into an unreadable reduction.
5. No new class may be added during draw.io layout without first being added to this inventory and the Relationship Matrix.
