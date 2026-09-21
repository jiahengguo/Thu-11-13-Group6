> 2026-09-17 修订说明：本文保留为原候选设计/历史审计，其中 43 类、59 条关系和 Pass 结论不再代表当前版本。当前实图见 [Current Model](G-04_Current_Model.md)，重新核对结果见 [Course Compliance Audit](G-04_Course_Compliance_Audit.md)。

# G-04 Class Diagram Optimisation Audit

## 1. Audit objective

This audit records each optimisation applied to the TripMate AI Elementary Structure Model and verifies that simplification does not remove content required by ELEC5620 Week 6 or the Stage 1 marking criterion.

Authoritative requirement source: `docs/TripMate AI.md`.

Final artefact: `G-04_Elementary_Structure_Modelling.drawio`.

## 2. Baseline and final result

| Measure | Exhaustive merged model | Optimised submission model | Change |
| --- | ---: | ---: | ---: |
| UML classifiers/elements | 88 | 43 | -51.1% |
| Relationships | 95 | 59 | -37.9% |
| Diagram pages | 1 | 1 | Unchanged |
| Classifier overlaps | 0 | 0 | Pass retained |
| Shared connector segments | 0 | 0 | Pass retained |
| Broken relationship endpoints | 0 | 0 | Pass retained |

The optimisation changes modeling granularity, not business scope. The final diagram remains a single unlimited-canvas model.

## 3. Step-by-step optimisation audit

### Step 1 - Apply the major-class test

Each candidate was assessed using three questions:

1. Does it have independent identity?
2. Does it have an independent lifecycle or meaningful state changes?
3. Does it own behaviour or participate in an important structural relationship?

Candidates that satisfied none or only a weak form of these tests were converted to attributes, operation parameters/returns, or omitted from the submission diagram.

Course check: Week 6 asks for the major design classes, not every noun in the requirements. **Pass.**

### Step 2 - Remove standalone type vocabulary

Removed as independent boxes:

- `Money` and `DateRange` DataTypes;
- `CaseStatus`, `OfferStatus`, `PlanStatus`, `MembershipTier`, `EntitlementOutcome`, `ReviewOutcome`, `ApprovalDecision`, and `RankingMode` Enumerations.

These names remain visible as attribute and operation types. No semantic information needed to understand the structure is lost.

Course check: typed attributes remain present; UML does not require every type to be expanded as a classifier. **Pass.**

### Step 3 - Fold constraints back into their owning classes

The six standalone constraint elements were removed. Their expressions are retained in the relevant class compartments:

| Constraint | Final owner |
| --- | --- |
| Immutable itinerary versions | `ItineraryVersion` |
| Approved and unexpired offer selection | `SupplierOffer` |
| Positive selling price and minimum margin | `PriceBreakdown` |
| Free-tier plan and duration limits | `MembershipPlan` |
| One active primary handler | `CaseAssignment` |
| Human approval for restricted commitments | `HumanApproval` |

Course check: constraints remain explicit and attached to the classifier they constrain. **Pass.**

### Step 4 - Remove optional and secondary-detail classifiers

Removed from the submission diagram include:

- analytics and optional acquisition detail: `Lead`, `CampaignMetric`, `AnalysisReport`, `CampaignResponse`;
- detailed itinerary/product subtypes: `TripLeg`, `AccommodationStay`, `ActivitySelection`, `TransportProduct`, `AccommodationProduct`, `ActivityProduct`;
- secondary exception automation: `ExternalUpdate`, `DisruptionNotification`, `HumanReferral`;
- supplier/campaign implementation detail: `SupplierAgreement`, `CampaignCostItem`, `MemberOfferRule`, `SupplierReliabilitySummary`;
- supporting value/results: `TravelRequest`, `ConstraintSet`, `ValidationResult`, `GuidanceDocument`;
- secondary boundary/persistence detail: `IAccessControlService`, `AccessControlService`, `IKnowledgeRetrievalService`, `ITraceRepository`, `TraceRepository`;
- generic modeling helpers: `Reviewable`, `Approvable`, `Policy`.

Relevant information remains represented through attributes, operations, the retained core records, or requirements text.

Course check: selected Optional Features do not need full implementation detail in an elementary structure model. The diagram still covers all core business areas. **Pass.**

### Step 5 - Preserve the required interface pattern

The final diagram retains five explicit service interfaces:

- `ILLMService`;
- `IEntitlementService`;
- `IConstraintValidationService`;
- `IPricingService`;
- `IReviewService`.

It also retains five corresponding implementations:

- `LLMAdapter`;
- `EntitlementService`;
- `ConstraintValidationService`;
- `PricingService`;
- `ReviewerGuardrail`.

Every implementation has a UML realization arrow to its interface. Agent dependencies point toward the required interface, not the implementation.

Course check: interfaces and implementation classes are both demonstrated correctly. **Pass.**

### Step 6 - Preserve required association semantics

The optimised diagram contains:

| UML relationship | Count | Representative example |
| --- | ---: | --- |
| Generalization | 6 | `TravelPlanningAgent -> Agent` |
| Composition | 6 | `TravelPlan -> ItineraryVersion` |
| Shared aggregation | 1 | `CampaignProposal -> SupplierOffer` |
| Directed association | 30 | `ExternalRequest -> Case` |
| Bidirectional association | 2 | `Traveller <-> TravelPlan` |
| Dependency | 9 | `TravelPlanningAgent -> IReviewService` |
| Realization | 5 | `PricingService -> IPricingService` |

Course check: all relationship types explicitly requested in the project brief are present and used for defensible semantics. **Pass.**

### Step 7 - Remove a duplicate relationship

The exhaustive merge produced two `ExternalRequest -> Case` associations with different labels. They represented the same lifecycle transition. The final diagram retains only:

`ExternalRequest -> Case: produces after confirmation [1 to 0..*]`.

Course check: one semantic fact is represented once. **Pass.**

### Step 8 - Restore relationships that simplification must not remove

Semantic review restored the following essential relationships:

- `Case -> AgentRun` for processing traceability;
- `Case -> EntitlementDecision` for entitlement history;
- `CustomerCase -> TravelPlan` for planning/revision outcomes;
- `SupplierCase -> SupplierOffer` for supplier assessment;
- `ItineraryVersion -> ItineraryVersion` for immutable revision history;
- `SupplierPartnershipAgent -> CampaignProposal` for responsibility;
- `CampaignProposal -> HumanApproval` for approval history;
- specialist Agent dependencies on validation and review interfaces.

Course check: the final static structure remains traceable to the major Use Case responsibilities and lifecycle requirements. **Pass.**

### Step 9 - Verify attributes and operations

- Attributes use `name: Type` notation and private visibility by default.
- Business operations use typed parameters and return types.
- Constructors, getters, setters, UI handlers, endpoints, and CRUD noise are omitted.
- Passive history records remain mostly attribute-oriented.
- Abstract classifiers and interfaces use explicit UML stereotypes.

Course check: classes contain appropriate attributes and methods without becoming code-level implementation diagrams. **Pass.**

### Step 10 - Verify multiplicity and direction

- Every structural association label records both endpoint multiplicities.
- Generalization points from child to parent.
- Realization points from implementation to interface.
- Composition diamonds remain on lifecycle owners.
- The shared aggregation diamond remains on `CampaignProposal` because offers exist independently.
- Dependencies point from clients to supplied interfaces.

Course check: multiplicity, navigability, ownership, and inheritance direction are explicit. **Pass.**

### Step 11 - Geometry and export audit

Automated checks on the final draw.io source report:

- 43 unique classifiers;
- 59 unique relationships;
- one diagram page with infinite-canvas mode;
- zero overlapping classifier rectangles;
- zero shared connector segments;
- zero broken relationship endpoints;
- orthogonal connectors with line jumps enabled for unavoidable crossings.

The final layout centers short classifier rows, aligns interfaces above their implementations, places the abstract `Agent` between its concrete subclasses, orders business classifiers by relationship flow, and distributes cross-layer routing across both left and right gutters instead of concentrating all lines on one side.

Visual style follows the supplied prior-year reference: white class boxes, thin dark grey-blue borders, restrained stereotypes, and generous whitespace.

## 4. Course compliance gate

| Criterion | Result |
| --- | --- |
| Major design-time classes identified | Pass |
| Appropriate attributes and operations | Pass |
| Associations and two-ended multiplicities | Pass |
| Generalization | Pass |
| Composition | Pass |
| Aggregation | Pass |
| Interfaces and implementation realization | Pass |
| Navigability/dependency direction | Pass |
| Constraints retained | Pass |
| No runtime object instances | Pass |
| No UI/database/deployment over-modeling | Pass |
| Single readable editable source | Pass |

## 5. Remaining reconciliation work

The Class Diagram is structurally ready. These external consistency checks remain when team artefacts become available:

1. Map SD-01, SD-02, and SD-03 messages to final operations.
2. Reconcile SM-01, SM-02, and SM-03 states with the typed status attributes.
3. Update UC-05 step 3 and its acceptance criteria to use `ExternalRequest -> confirmation -> Case` consistently.
4. Add the final document version/source note before submission export.

These are cross-model checks; they do not justify restoring the removed secondary classifiers unless a behaviour diagram demonstrates a genuine missing responsibility.
