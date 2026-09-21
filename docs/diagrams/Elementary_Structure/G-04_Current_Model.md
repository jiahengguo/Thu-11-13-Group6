# G-04 当前类图清单（自动生成）

2026-09-17：48 个分类器，69 条关系。此文件对应当前 drawio；旧 Inventory/Relationship Matrix 是候选设计资料。

## 类与成员

### ILLMService

类型：interface

```text
---
+extract(input: String, schema: String): ExtractionResult
+draft(context: String): String
+explain(result: String): String
```

### IEntitlementService

类型：interface

```text
---
+evaluate(traveller: Traveller, action: RequestedAction, dates: DateRange [0..1]): EntitlementDecision
```

### IConstraintValidationService

类型：interface

```text
---
+validatePlan(version: ItineraryVersion): ValidationResult
+validateProposal(subject: SubjectRef): ValidationResult
+validateOffer(offer: SupplierOffer): ValidationResult
```

### IPricingService

类型：interface

```text
---
+calculate(offer: SupplierOffer, discount: Money): PriceBreakdown
+checkMargin(breakdown: PriceBreakdown): Boolean
```

### IReviewService

类型：interface

```text
---
+review(subject: SubjectRef, evidence: Evidence[*]): ReviewResult
```

### LLMAdapter

类型：adapter

```text
-modelReference: String
---
+extract(input: String, schema: String): ExtractionResult
+draft(context: String): String
+explain(result: String): String
```

### EntitlementService

类型：service

```text
-ruleVersion: String
---
+evaluate(traveller: Traveller, action: RequestedAction, dates: DateRange [0..1]): EntitlementDecision
```

### ConstraintValidationService

类型：service

```text
-ruleSetVersion: String
---
+validatePlan(version: ItineraryVersion): ValidationResult
+validateProposal(subject: SubjectRef): ValidationResult
+validateOffer(offer: SupplierOffer): ValidationResult
```

### PricingService

类型：service

```text
-configVersion: String
-minimumMargin: Money
---
+calculate(offer: SupplierOffer, discount: Money): PriceBreakdown
+checkMargin(breakdown: PriceBreakdown): Boolean
```

### ReviewerGuardrail

类型：service

```text
-reviewerId: String
-policyVersion: String
---
+review(subject: SubjectRef, evidence: Evidence[*]): ReviewResult
```

### OperationsAgent

类型：class

```text
-routingRulesVersion: String
-requiredFieldRulesVersion: String
---
+intake(request: ExternalRequest): Case[*]
+route(case: Case): CaseAssignment
+releaseResponse(case: Case): void
```

### TravelPlanningAgent

类型：class

```text
-defaultRankingMode: RankingMode
---
+createPlan(request: TravelRequest): TravelPlan
+createRevision(baseline: ItineraryVersion, amendment: String): ItineraryVersion
+compareVersions(baseline: ItineraryVersion, revision: ItineraryVersion): PlanComparison
```

### Agent

类型：abstract

```text
-agentId: String
-status: AgentStatus
---
+handleCase(case: Case): AgentResult
+requestReview(subject: SubjectRef): ReviewResult
+recordTrace(entry: TraceEntry): void
```

### CustomerExceptionAgent

类型：class

```text
-confidenceThreshold: Decimal
---
+investigate(issue: ExceptionIssue): ExceptionCase
+prepareRecovery(case: ExceptionCase): RecoveryProposal
+recommendResolution(case: ExceptionCase): ResolutionRecommendation
```

### SupplierPartnershipAgent

类型：class

```text
-pricingConfigVersion: String
---
+assessOffer(case: SupplierCase, evidence: Evidence[*]): SupplierOffer
+prepareCampaign(brief: CampaignBrief): CampaignProposal
+summariseReliability(supplier: Supplier, period: DateRange): SupplierReliabilitySummary
```

### Traveller

类型：class

```text
-travellerId: String
-displayName: String
---
+submitRequest(content: String): ExternalRequest
+confirmRequest(requestId: String): void
+confirmAmendment(amendment: String): void
```

### Subscription

类型：class

```text
-subscriptionId: String
-status: SubscriptionStatus
-validityPeriod: DateRange
---
+isActive(on: Date): Boolean
```

### MembershipPlan

类型：class

```text
-planId: String
-tier: MembershipTier
-featureEntitlements: String[*]
{FREE: PLANNED + ACTIVE <= 2; inclusive days <= 5}
---
+allowsFeature(featureId: String): Boolean
```

### ExternalRequest

类型：class

```text
-requestId: String
-sourceChannel: SourceChannel
-classificationConfidence: Decimal
-confirmed: Boolean
-requesterKind: RequesterKind
-sourceCampaignId: String [0..1]
{Traveller xor Supplier for direct intake}
-humanRequestCount: Integer
---
+identifyMissingFields(): String[*]
+confirm(): void
```

### Case

类型：abstract

```text
-caseId: String
-status: CaseStatus
-createdAt: DateTime
-confirmedAt: DateTime
---
+close(reason: ClosureReason): void
+escalate(reason: String): void
```

### CaseAssignment

类型：class

```text
-role: AssignmentRole
-assignedAt: DateTime
-releasedAt: DateTime [0..1]
-status: AssignmentStatus
{active PRIMARY_HANDLER <= 1 per Case}
{COORDINATOR must be OperationsAgent}
---
+assign(): void
+release(): void
```

### CustomerCase

类型：class

```text
-caseType: CustomerCaseType
-riskLevel: RiskLevel
---
+requestClarification(question: String): void
```

### SupplierCase

类型：class

```text
-caseType: SupplierCaseType
-supplierReference: String
---
+requestSupplierCorrection(reason: String): void
```

### Supplier

类型：class

```text
-supplierId: String
-name: String
-eligibilityStatus: SupplierStatus
---
+submitOffer(source: Evidence): ExternalRequest
+provideCorrection(offerId: String): ExternalRequest
```

### HumanFounderOperator

类型：class

```text
-operatorId: String
-authorityScope: String[*]
---
+decide(subject: SubjectRef, decision: ApprovalDecision): HumanApproval
+submitCampaignBrief(brief: CampaignBrief): CampaignProposal
+takeOver(case: Case): void
```

### EntitlementDecision

类型：class

```text
-decisionId: String
-outcome: EntitlementOutcome
-reason: String
-decidedAt: DateTime
---
+explainsFailure(): String
```

### TravelPlan

类型：class

```text
-planId: String
-status: PlanStatus
-travelDates: DateRange
---
+currentVersion(): ItineraryVersion [0..1]
+addVersion(version: ItineraryVersion): void
```

### ItineraryVersion

类型：class

```text
-versionId: String
-versionNo: Integer
-status: PlanStatus
-rankingMode: RankingMode
-totalPrice: Money
{confirmed content frozen; amendment creates successor}
{feasible version has at least one item}
---
+calculateDuration(): Integer
+compareTo(other: ItineraryVersion): PlanComparison
```

### PlanComparison

类型：class

```text
-changedFields: String[*]
-priceDelta: Money
-tradeOffs: String[*]
{baseline != revision; same TravelPlan}
---
+renderExplanation(): String
```

### ItineraryItem

类型：entity

```text
-itemId: String
-startAt: DateTime
-endAt: DateTime
-quotedPrice: Money
-kind: ItineraryItemKind
---
+validateTiming(): ValidationResult
```

### SupplierOffer

类型：class

```text
-offerId: String
-status: OfferStatus
-availableQuantity: Integer
-validUntil: DateTime
-supplierCost: Money
{APPROVED and unexpired before selection}
---
+isSelectable(at: DateTime): Boolean
+expire(): void
+invalidateCurrentDecisions(): void
```

### TravelProduct

类型：entity

```text
-productId: String
-name: String
-productType: ProductType
---
+describe(): String
```

### PriceBreakdown

类型：class

```text
-supplierCost: Money
-markupRate: Decimal
-basePrice: Money
-discountAmount: Money
-sellingPrice: Money
-marginAmount: Money
{AUD; sellingPrice.amount > 0; margin >= minimum}
---
+passesMinimumMargin(minimum: Money): Boolean
```

### ConstraintSet

类型：class

```text
-constraintSetId: String
-hardConstraints: Constraint[*]
-preferences: Preference[*]
{confirmed snapshot; amendment creates new set}
---
+conflictsWith(other: ConstraintSet): String[*]
+changedFields(other: ConstraintSet): String[*]
```

### TravelRequest

类型：class

```text
-requestId: String
-origin: String
-destination: String
-partySize: Integer
-budgetCeiling: Money
-travelDates: DateRange
-rankingMode: RankingMode
---
+validateCompleteness(): ValidationResult
+toConstraintSet(): ConstraintSet
```

### ValidationResult

类型：class

```text
-passed: Boolean
-failedRules: String[*]
-checkedAt: DateTime
---
```

### ExceptionCase

类型：class

```text
-exceptionCaseId: String
-status: ExceptionStatus
-confidence: Decimal
---
+recordFinding(finding: String): void
+referToHuman(reason: String): void
```

### ExceptionIssue

类型：entity

```text
-issueId: String
-reportedAt: DateTime
-severity: Severity
-description: String
-kind: ExceptionIssueKind
---
+affectedItems(): ItineraryItem[*]
```

### RecoveryProposal

类型：class

```text
-proposalId: String
-status: ProposalStatus
-budgetImpact: Money
-timingImpact: String
-affectedVersionId: String
---
+validate(): ValidationResult
+revise(reasons: String[*]): RecoveryProposal
```

### ResolutionRecommendation

类型：class

```text
-recommendationId: String
-status: ProposalStatus
-recommendedResponse: String
-restrictedCommitment: Boolean
---
+validate(): ValidationResult
+revise(reasons: String[*]): ResolutionRecommendation
```

### CampaignProposal

类型：class

```text
-campaignId: String
-status: CampaignStatus
-targetAudience: String
-channel: SourceChannel
-campaignDates: DateRange
-budgetCeiling: Money
-promotionalContent: String
-estimatedCost: Money
{approval needs eligible offers and passed review}
---
+calculateEstimatedCost(): Money
+invalidateApproval(): void
+isEligibleForSimulation(): Boolean
```

### CampaignBrief

类型：class

```text
-briefId: String
-objective: String
-audience: String
-channel: SourceChannel
-dates: DateRange
-budgetCeiling: Money
-restrictions: String[*]
---
+validateCompleteness(): ValidationResult
```

### MemberOfferRule

类型：class

```text
-ruleId: String
-eligibleTiers: MembershipTier[*]
-discountAmount: Money
-validityPeriod: DateRange
---
+isApplicable(offer: SupplierOffer, tier: MembershipTier): Boolean
```

### AgentRun

类型：class

```text
-runId: String
-startedAt: DateTime
-completedAt: DateTime [0..1]
-status: RunStatus
---
+start(): void
+finish(status: RunStatus): void
```

### TraceEntry

类型：class

```text
-timestamp: DateTime
-eventType: TraceEventType
-subjectType: String
-subjectId: String
-summary: String
---
```

### Evidence

类型：class

```text
-evidenceId: String
-sourceType: String
-sourceReference: String
-capturedAt: DateTime
---
```

### ReviewResult

类型：class

```text
-reviewId: String
-outcome: ReviewOutcome
-reasons: String[*]
-reviewedAt: DateTime
-approvalRequired: Boolean
-subject: SubjectRef
---
+passed(): Boolean
```

### HumanApproval

类型：class

```text
-approvalId: String
-decision: ApprovalDecision
-reason: String
-scope: String
-decidedAt: DateTime
-subject: SubjectRef
{required for restricted commitments}
---
+permits(subject: SubjectRef): Boolean
```

## 当前关系

多重性列表示写在该类端的数量，不是沿箭头读取的动作次数。

| ID | 源类 | 源端多重性 | 关系 | 类型 | 目标类 | 目标端多重性 |
|---|---|---|---|---|---|---|
| R001 | CustomerCase | — | — | generalization | Case | — |
| R002 | SupplierCase | — | — | generalization | Case | — |
| R003 | OperationsAgent | — | — | generalization | Agent | — |
| R004 | TravelPlanningAgent | — | — | generalization | Agent | — |
| R005 | CustomerExceptionAgent | — | — | generalization | Agent | — |
| R006 | SupplierPartnershipAgent | — | — | generalization | Agent | — |
| R007 | Traveller | 0..1 | submits | association | ExternalRequest | 0..* |
| R008 | Supplier | 0..1 | submits | association | ExternalRequest | 0..* |
| R009 | ExternalRequest | 1 | produces after confirmation | association | Case | 0..* |
| R010 | Case | 1 | retains | composition | CaseAssignment | 0..* |
| R011 | CaseAssignment | 0..* | assigns | association | Agent | 1 |
| R012 | Traveller | 1 | holds | association | Subscription | 0..* |
| R013 | Subscription | 0..* | applies | association | MembershipPlan | 1 |
| R014 | Traveller | 1 | owns | bidir | TravelPlan | 0..* |
| R015 | TravelPlan | 1 | contains | composition | ItineraryVersion | 0..* |
| R016 | ItineraryVersion | 1 | comprises | composition | ItineraryItem | 0..* |
| R017 | ItineraryItem | 0..* | selects | association | SupplierOffer | 1 |
| R018 | Supplier | 1 | provides | bidir | SupplierOffer | 0..* |
| R019 | SupplierOffer | 0..* | offers | association | TravelProduct | 1 |
| R020 | SupplierOffer | 1 | owns history | composition | PriceBreakdown | 0..* |
| R021 | CustomerCase | 1 | opens | association | ExceptionCase | 0..1 |
| R022 | ExceptionCase | 1 | investigates | composition | ExceptionIssue | 1 |
| R023 | ExceptionCase | 1 | produces | association | RecoveryProposal | 0..* |
| R024 | ExceptionCase | 1 | produces | association | ResolutionRecommendation | 0..* |
| R025 | CampaignProposal | 0..* | selected offers | aggregation | SupplierOffer | 0..* |
| R026 | Agent | 1 | executes | association | AgentRun | 0..* |
| R027 | Agent | — | «uses» | dependency | ILLMService | — |
| R028 | OperationsAgent | — | «uses» | dependency | IEntitlementService | — |
| R029 | TravelPlanningAgent | — | «uses» | dependency | IConstraintValidationService | — |
| R030 | CustomerExceptionAgent | — | «uses» | dependency | IReviewService | — |
| R031 | SupplierPartnershipAgent | — | «uses» | dependency | IPricingService | — |
| R032 | ReviewerGuardrail | — | — | realization | IReviewService | — |
| R033 | Traveller | 1 | receives | association | EntitlementDecision | 0..* |
| R034 | EntitlementService | — | — | realization | IEntitlementService | — |
| R035 | CustomerCase | 1 | captures | composition | TravelRequest | 0..1 |
| R036 | TravelRequest | 1 | normalises to | composition | ConstraintSet | 1 |
| R037 | TravelPlanningAgent | 1 | creates | association | TravelPlan | 0..* |
| R038 | PlanComparison | 0..* | baseline | association | ItineraryVersion | 1 |
| R039 | ItineraryVersion | 1 | validated by | association | ValidationResult | 0..* |
| R040 | CustomerExceptionAgent | 1 | handles | association | ExceptionCase | 0..* |
| R041 | RecoveryProposal | 0..* | proposes | association | ItineraryVersion | 1 |
| R042 | ExceptionCase | 0..* | collects | association | Evidence | 0..* |
| R043 | SupplierOffer | 0..* | supported by | association | Evidence | 1..* |
| R044 | PricingService | — | — | realization | IPricingService | — |
| R045 | HumanFounderOperator | 1 | submits | association | CampaignBrief | 0..* |
| R046 | CampaignBrief | 1 | drives | association | CampaignProposal | 0..* |
| R047 | CampaignProposal | 1 | defines | composition | MemberOfferRule | 0..1 |
| R048 | MemberOfferRule | 0..* | applies to | association | SupplierOffer | 1..* |
| R049 | AgentRun | 1 | records | composition | TraceEntry | 0..* |
| R050 | LLMAdapter | — | — | realization | ILLMService | — |
| R051 | ReviewerGuardrail | 1 | creates | association | ReviewResult | 0..* |
| R052 | ReviewResult | 0..* | considers | association | Evidence | 1..* |
| R053 | HumanFounderOperator | 1 | decides | association | HumanApproval | 0..* |
| R054 | ConstraintValidationService | — | — | realization | IConstraintValidationService | — |
| R055 | Case | 0..1 | processed by | association | AgentRun | 0..* |
| R056 | Case | 1 | requires | association | EntitlementDecision | 0..* |
| R057 | CustomerCase | 0..* | concerns | association | TravelPlan | 0..1 |
| R058 | SupplierCase | 0..* | assesses | association | SupplierOffer | 0..1 |
| R059 | ItineraryVersion | 0..* | revises | association | ItineraryVersion | 0..1 |
| R060 | SupplierPartnershipAgent | 1 | prepares | association | CampaignProposal | 0..* |
| R061 | CampaignProposal | 1 | approval history | association | HumanApproval | 0..* |
| R062 | CustomerExceptionAgent | — | «uses» | dependency | IConstraintValidationService | — |
| R063 | SupplierPartnershipAgent | — | «uses» | dependency | IConstraintValidationService | — |
| R064 | TravelPlanningAgent | — | «uses» | dependency | IReviewService | — |
| R065 | SupplierPartnershipAgent | — | «uses» | dependency | IReviewService | — |
| R066 | PlanComparison | 0..* | revision | association | ItineraryVersion | 1 |
| R067 | ItineraryVersion | 0..* | applies snapshot | association | ConstraintSet | 1 |
| R068 | ExceptionIssue | 0..* | affects | association | ItineraryVersion | 0..1 |
| R069 | OperationsAgent | 1 | coordinates | association | ExternalRequest | 0..* |
