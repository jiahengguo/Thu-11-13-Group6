# TripMate AI

[English](README.md) | [简体中文](README.zh-CN.md)

> A feasibility study of an AI-native one-person travel company that solves real customer problems through specialised agents, deterministic tools, and human oversight.

## Project status

TripMate AI is currently in the **requirements, business validation, and architecture design stage** for ELEC5620. The repository does not yet contain a working prototype. This README describes the agreed product direction, MVP scope, operating model, planned architecture, evaluation approach, and future development.

Under the course's permitted application areas, TripMate AI is classified as a **Smart Personal Assistant** specialised in travel services. More specifically, it is a feasibility prototype for an **LLM-powered multi-agent One-Person Company (OPC)**, not merely a travel recommendation application.

## Vision

TripMate AI investigates a practical question:

**Can one human operator run a trustworthy travel service company with the support of multiple specialised AI agents?**

The objective is not to build another itinerary chatbot. The project treats TripMate AI as a real company that must acquire and understand customers, deliver a reliable service, respond when plans fail, manage complaints, control cost, protect data, and know when a human must take responsibility.

The human operator remains accountable for the company. AI agents act as virtual departments, but they do not independently perform real bookings, payments, refunds, legal decisions, or safety-critical actions.

## Alignment with the ELEC5620 project

The repository is organised around the requirements in the official course description.

| Course requirement | TripMate AI response | Planned evidence |
| --- | --- | --- |
| One-Person AI Company | One human operator supervises a virtual travel company staffed by specialised agents. | OPC operating model, operator dashboard, approval queue, and workload metrics. |
| LLM-powered multi-agent system | Agents hold different company roles and collaborate through controlled delegation. | Agent definitions, orchestration traces, collaboration and sequence diagrams. |
| Planning and decision-making | Travel Manager decomposes requests; specialists generate and revise checked proposals. | Activity/sequence models and end-to-end scenarios. |
| External tool use | Agents use transport, weather, budget, conflict, order, and policy tools. | Structured tool contracts, integration tests, and execution logs. |
| Adapt actions based on results | Tool failures, disruptions, customer revisions, and complaints trigger re-planning or escalation. | State machines, failure scenarios, plan versions, and complaint workflow. |
| Model-based software engineering | Requirements, architecture, behaviours, implementation, tests, and acceptance evidence remain traceable. | Stage 1 report, UML/model set, traceability matrix, and Stage 2 prototype. |
| Agile group development | Three members work through a shared backlog, short sprints, reviews, and retrospectives. | GitHub Issues/Projects, sprint records, commits, pull-request reviews, and contribution log. |
| Advanced technology | LLM orchestration is combined with tool calling, guardrails, structured outputs, tracing, and optional RAG. | Prototype implementation and technical evaluation. |

### Course deliverables

- **Stage 1 — 30 marks:** formal requirements/architecture/modelling report (15 marks), plus presentation and interview (15 marks).
- **Stage 2 — 20 marks:** architecture-aligned proof-of-concept implementation and stakeholder demonstration.
- The Stage 1 document must clearly identify each member's contribution.
- The Stage 2 source code must be submitted through Canvas before Monday of the final week; the demonstration takes place in the final week.
- Exact internal team deadlines will be recorded in the Agile plan once the Canvas schedule is confirmed.

## Real user problems

| User pain point | Why current solutions are insufficient | TripMate AI response |
| --- | --- | --- |
| Planning information is fragmented | Travellers compare transport, hotels, activities, weather, and budgets across many sites. | Build one constraint-aware plan from structured data and explain the trade-offs. |
| “Best” means different things | Cheapest, fastest, and most comfortable options are rarely the same. | Offer Comfort, Value, and Budget modes with transparent, configurable scoring. |
| Hidden constraints are easily missed | Baggage, accessibility, arrival time, transfers, and activity schedules can invalidate a plan. | Apply hard constraints before ranking and run deterministic budget/conflict checks. |
| Plans become obsolete | Weather, cancellations, price changes, and venue closures can break an itinerary. | Detect affected items, generate alternatives, and preserve auditable plan versions. |
| Automated support lacks accountability | Customers often receive generic replies and repeat their story after a problem occurs. | Connect complaints to the order, evidence, policy, agent trace, and a clear escalation path. |
| Travellers do not know whether AI information is reliable | Generative systems can invent prices, availability, and policies. | Separate LLM reasoning from verified data tools, show sources/timestamps, and refuse unsupported claims. |

## Target users and initial market

The MVP focuses on individual travellers planning short Australian domestic trips. The first supported scenario is a Sydney–Melbourne trip using simulated transport, accommodation, activity, and disruption data.

Initial user groups include:

- Budget-conscious students and solo travellers.
- Time-constrained travellers who value a fast comparison of valid options.
- Customers who need a clear recovery path when a plan changes.
- A human travel-service operator who needs visibility, approval controls, and manageable workload.

## Value proposition

For travellers, TripMate AI offers one place to plan, compare, revise, and resolve problems. For the operator, it automates repetitive research and support work while retaining control over financial, legal, and high-risk decisions.

The OPC hypothesis is considered feasible only if the system can demonstrate that:

- A single operator can supervise several simultaneous customer journeys.
- Routine planning and support tasks are completed with acceptable quality.
- Exceptions are prioritised instead of overwhelming the operator.
- Recommendations are traceable to data and business rules.
- Model/API cost and human handling time remain proportionate to the value delivered.
- Customers have a clear route to correction, complaint, and human review.

## Company operating model

```mermaid
flowchart LR
    Acquire[Customer acquisition] --> Consult[Consultation]
    Consult --> Plan[Plan and quote]
    Plan --> Confirm[Customer confirmation]
    Confirm --> Support[In-trip support]
    Support --> Recover[Disruption recovery]
    Recover --> AfterSales[After-sales and complaints]
    AfterSales --> Learn[Quality review and improvement]
    Learn --> Consult
```

The course prototype concentrates on consultation through after-sales support. Customer acquisition, billing, supplier contracts, and profitability are modelled as business capabilities and future validation areas rather than fully implemented services.

## AI agent organisation

| Agent | Virtual company role | Responsibilities |
| --- | --- | --- |
| Customer Service Agent | Front desk | Detect intent, collect missing information, answer routine questions, and route planning or complaint requests. |
| Travel Manager Agent | Operations manager | Own the case, decompose work, coordinate specialists, combine results, and manage the service lifecycle. |
| Fare Planning Agent | Transport specialist | Filter transport options, apply the selected travel mode, rank candidates, and explain trade-offs. |
| Itinerary Agent | Travel consultant | Coordinate accommodation, activities, transport times, customer preferences, and budget. |
| Disruption Agent | Recovery specialist | Identify affected items and propose alternatives after weather changes, delays, cancellations, or closures. |
| Complaint Agent | Resolution specialist | Classify complaints, collect evidence, check policy, propose resolutions, and escalate high-risk cases. |
| Reviewer/Guardrail | Quality and compliance | Check constraints, arithmetic, conflicts, evidence, policy, confidence, and authorisation. |

The Travel Manager owns each case. Specialist agents cannot make unrestricted order changes. Every hand-off, tool call, material decision, and approval is recorded.

## High-level architecture

```mermaid
flowchart TB
    Customer[Customer interface] --> API[Application API]
    Operator[OPC operator dashboard] --> API
    API --> Service[Customer Service Agent]
    Service --> Manager[Travel Manager Agent]
    Service --> Complaint[Complaint Agent]
    Manager --> Fare[Fare Planning Agent]
    Manager --> Itinerary[Itinerary Agent]
    Manager --> Disruption[Disruption Agent]
    Fare --> TransportTools[Transport search and scoring]
    Itinerary --> PlanTools[Accommodation activity budget conflict]
    Disruption --> EventTools[Weather and disruption events]
    Complaint --> SupportTools[Orders policies complaint records]
    Fare --> Review[Reviewer and guardrails]
    Itinerary --> Review
    Disruption --> Review
    Complaint --> Review
    API --> Data[(Customers plans orders complaints)]
    Manager --> Trace[(Agent and audit traces)]
    Complaint --> Human[Human approval queue]
```

### Proposed implementation stack

- Python and FastAPI for the application service.
- One agent orchestration framework, selected after a small technical spike.
- Streamlit for the first customer/operator interface; React is a future option.
- SQLite for the prototype and PostgreSQL as a later production option.
- Pydantic schemas and deterministic domain services for validation.
- Pytest for unit, integration, scenario, and regression tests.
- GitHub Issues/Projects for the Agile backlog and contribution evidence.

## Core travel modes

| Factor | Comfort | Value | Budget |
| --- | ---: | ---: | ---: |
| Price | 20% | 40% | 65% |
| Journey time | 30% | 25% | 15% |
| Comfort | 35% | 20% | 5% |
| Reliability/transfers | 15% | 15% | 15% |

These are initial configurable weights. Hard constraints—such as budget ceiling, dates, latest arrival, baggage, accessibility, transfer limit, overnight travel, availability, and cancellation status—are applied before scoring.

```text
score = price_score * Wp
      + duration_score * Wt
      + comfort_score * Wc
      + reliability_score * Wr
```

The LLM extracts preferences and explains results. Deterministic code filters options, performs arithmetic, detects conflicts, and ranks candidates. A recommendation must include alternatives, a cost breakdown, trade-offs, data timestamps, and excluded options with reasons.

## Core customer workflows

### 1. Plan and compare

1. The customer provides route, dates, budget, travel mode, preferences, and hard constraints.
2. Customer Service validates the request and asks for missing information.
3. Travel Manager creates a structured case and delegates research.
4. Fare Planning filters and ranks transport options.
5. Itinerary Agent adds accommodation and activities.
6. Budget and schedule tools validate the plan.
7. Reviewer checks evidence, policy, constraints, and confidence.
8. The customer receives a recommended plan, alternatives, and explanations.
9. Customer confirmation creates a simulated order and immutable plan version.

### 2. Change preference mode

The customer can switch between Comfort, Value, and Budget. The system recalculates the plan and displays differences in price, duration, transfers, comfort, reliability, and affected activities.

### 3. Recover from disruption

An event is matched to the active itinerary, affected items are identified, alternatives are generated, budget/conflict checks run again, and the customer chooses whether to accept a new version. The original plan remains available for audit and complaint investigation.

### 4. Handle a complaint

The Complaint Agent links the complaint to an order, conversation, quote, data snapshot, and execution trace. It classifies the category and severity, checks company policy, proposes a resolution, and requests human approval when required.

```mermaid
stateDiagram-v2
    [*] --> Received
    Received --> InformationRequired
    InformationRequired --> Investigating
    Received --> Investigating
    Investigating --> ResolutionProposed
    Investigating --> Escalated
    ResolutionProposed --> AwaitingApproval
    ResolutionProposed --> AwaitingCustomer
    AwaitingApproval --> AwaitingCustomer
    AwaitingCustomer --> Resolved
    AwaitingCustomer --> Reopened
    Reopened --> Investigating
    Resolved --> [*]
```

P1 safety issues and P2 cancellations or material financial disputes are prioritised for human attention. Human approval is mandatory for safety concerns, legal threats, uncertain policies, compensation above a threshold, low-confidence responsibility decisions, and repeated customer rejection.

## Real company challenges and responses

| Challenge | Prototype response | Longer-term direction |
| --- | --- | --- |
| Customer trust | Explain recommendations, show data timestamps, preserve versions, and offer human review. | Supplier-level provenance, verified reviews, service guarantees, and transparent terms. |
| Hallucination and bad data | Structured tool results, deterministic validation, refusal when evidence is missing. | Multiple data providers, freshness monitoring, and automated data-quality scoring. |
| Supplier/API failure | Simulated failures, timeout handling, retries, fallback data, and explicit degraded status. | Provider redundancy, circuit breakers, queues, and contractual SLAs. |
| Too many support cases for one operator | Severity classification, priority queue, confidence thresholds, and routine automated responses. | Workload forecasting, SLA alerts, and temporary human escalation partners. |
| Privacy and security | Minimise stored data, separate secrets, redact logs, and use role-based operator actions. | Encryption, retention/deletion controls, security review, consent management, and incident response. |
| Legal and financial liability | Clear prototype disclaimers and no real booking/refund actions. | Jurisdiction review, terms, insurance, licences, audit controls, and professional advice. |
| Service quality drift | Fixed scenario tests, trace review, customer feedback, and prompt/version tracking. | Continuous evaluation, regression dashboards, model routing, and release gates. |
| Unit economics | Record model calls, latency, tool usage, and operator handling time. | Pricing experiments, caching, smaller-model routing, and customer lifetime-value analysis. |
| Customer acquisition | Define target personas and value proposition. | Landing-page experiments, referral loops, partnerships, SEO, and acquisition-cost measurement. |
| Business continuity | Manual takeover and exportable case records. | Backups, monitoring, disaster recovery, and documented operating procedures. |

## Functional requirements

| ID | Requirement |
| --- | --- |
| FR-01 | Collect and validate structured travel requirements from natural language. |
| FR-02 | Support Comfort, Value, and Budget modes. |
| FR-03 | Apply hard constraints before scoring options. |
| FR-04 | Generate transport, accommodation, activity, and budget plans. |
| FR-05 | Explain recommendations, alternatives, trade-offs, and exclusions. |
| FR-06 | Calculate cost and detect schedule conflicts deterministically. |
| FR-07 | Support requirement revision and version comparison. |
| FR-08 | Detect disruption impact and propose checked alternatives. |
| FR-09 | Create, classify, investigate, escalate, and track complaints. |
| FR-10 | Consult order evidence and company policy before resolution. |
| FR-11 | Require human approval for configured high-risk actions. |
| FR-12 | Record agent hand-offs, tool calls, decisions, confidence, and outcomes. |
| FR-13 | Provide the operator with prioritised cases and an approval interface. |
| FR-14 | Capture customer feedback and link it to the delivered service. |

## Requirement classification

The Stage 1 report will maintain a versioned catalogue rather than treating every idea as equally committed.

### Agreed baseline

- TripMate AI is a Smart Personal Assistant and a multi-agent OPC feasibility prototype.
- One human operator remains accountable and supervises exceptional/high-risk cases.
- The MVP uses simulated data and actions; it performs no real booking, payment, or refund.
- The first end-to-end case is an Australian domestic individual trip.
- LLM outputs are checked by deterministic tools and guardrails where correctness matters.

### Mandatory capabilities

- Distinct business-role agents that collaborate, use tools, and react to results.
- Customer intake, three travel modes, plan generation, comparison, and explanation.
- Deterministic budget, constraint, and schedule validation.
- Disruption-driven re-planning and auditable itinerary versions.
- Customer complaint classification, investigation, resolution, and human escalation.
- Operator approval, agent/tool tracing, and testable acceptance criteria.
- Stage 1 model-to-Stage 2 implementation traceability.

### Optional features

- RAG for destination, supplier, and policy knowledge.
- Real weather or travel-data integration.
- Multilingual/voice interaction, mobile client, map visualisation, and proactive notifications.
- Long-term preference memory, analytics, supplier scoring, and commercial experiments.

Optional features may enter the MVP only after all mandatory acceptance tests pass.

## Non-functional requirements

- **Correctness:** money, time, constraints, and policy rules use deterministic services.
- **Explainability:** important outputs include evidence, rationale, and limitations.
- **Safety:** agents cannot perform real financial transactions or bypass approvals.
- **Privacy:** data collection is minimised; secrets and personal data are excluded from public logs.
- **Reliability:** tool failure produces a bounded retry, fallback, or explicit error.
- **Maintainability:** agents, tools, prompts, business rules, data, and UI are modular.
- **Traceability:** requirements map to models, components, tests, and demonstration cases.
- **Usability:** customers can understand, compare, correct, complain, and request human review.
- **Operability:** one operator can see priorities, failures, cost, and pending decisions.

## Role of the LLM

The prototype must demonstrate the LLM's contribution in the three areas named by the course:

| Capability | LLM contribution | Non-LLM control |
| --- | --- | --- |
| Perception | Understand free-text goals, preferences, complaints, and disruption descriptions; detect missing information. | Pydantic/schema validation, trusted data adapters, and input guardrails. |
| Decision-making | Decompose cases, choose specialists/tools, compare trade-offs, propose re-planning or resolution. | Hard constraints, scoring functions, policy rules, confidence thresholds, and human approval. |
| Interaction | Ask clarifying questions and explain plans, changes, limitations, and complaint outcomes. | Approved templates, source/timestamp display, audit logs, and output guardrails. |

The evaluation will include cases where the LLM should ask for clarification, call a tool, refuse to invent unavailable data, revise a plan after new evidence, and escalate rather than act autonomously.

## Design assumptions

- The first prototype supports only the configured Australian routes and sample inventory.
- Supplier, weather, and order data are simulated or provided through controlled APIs.
- Prices and availability are snapshots and are not commercial quotations.
- Each request represents one traveller with one active itinerary.
- The user provides truthful requirements and can correct extracted information before confirmation.
- Network, model, and tool calls may fail; the workflow must expose failure instead of fabricating a result.
- The human operator is available for queued high-risk decisions within the prototype demonstration.
- Course tutors act as project stakeholders for requirement finalisation and acceptance.

Assumptions will be assigned identifiers and revisited whenever a requirement or external dependency changes.

## Design rationale and considered alternatives

| Decision | Selected approach | Considered/discarded alternative | Rationale |
| --- | --- | --- | --- |
| Agent control | Manager-led orchestration with specialist tools/hand-offs. | Unrestricted group chat between all agents. | Clear ownership, predictable traces, simpler testing, and lower cost. |
| Correctness | LLM plus deterministic domain services. | Let the LLM calculate and rank everything. | Arithmetic, constraints, and policies need reproducible results. |
| Booking scope | Simulated transactions and human approval. | Connect to real payment/booking providers in the MVP. | Reduces legal, financial, security, and integration risk. |
| Data scope | Small controlled Australian dataset. | Global real-time travel marketplace. | Supports meaningful evaluation within a three-person course project. |
| Interface | Streamlit MVP with separate customer/operator views. | Full mobile and React platform immediately. | Preserves effort for agent behaviour, modelling, and evaluation. |
| Human role | Risk-based human-in-the-loop. | Fully autonomous OPC. | A realistic company needs accountability for exceptions and high-impact decisions. |

Decisions that are not selected will remain documented because the Stage 1 presentation must explain both chosen and discarded alternatives.

## Model set and traceability

The Stage 1 package is expected to contain:

- User Requirement Diagram and Feature Diagram.
- Use Case Diagram plus detailed principal use cases.
- Package Diagram, Class Diagram, Structured Class Diagram, and Collaboration Diagram.
- Activity Diagrams for planning, disruption recovery, and complaint handling.
- State Machines for travel requests/orders and complaints.
- Sequence Diagrams for planning, re-planning, complaint resolution, and human approval.
- Component relationships and extension points for future agents, tools, data providers, and interfaces.
- A traceability matrix linking requirement → use case/model → component → test → acceptance evidence.

The README diagrams are high-level orientation only and do not replace the formal Stage 1 models.

## Change assessment and acceptance

Every material change will be handled through a GitHub Issue containing the affected requirement IDs, rationale, priority, architecture/model impact, test impact, owner, and acceptance criteria.

A change is accepted only when:

1. Mandatory requirements and safety controls still pass.
2. Relevant diagrams and traceability links are updated.
3. Unit/integration/scenario tests provide evidence for the new behaviour.
4. The product owner/operator and relevant team reviewer approve the result.
5. Performance, model cost, operator workload, privacy, and new risks remain acceptable.

Tutor feedback that changes the agreed requirements will be recorded as a baseline revision rather than silently modifying the implementation.

## MVP boundaries

### Included

- Australian domestic short trips with a limited set of routes.
- Simulated transport, accommodation, activity, order, refund, and policy data.
- One traveller per request and one connected end-to-end demonstration.
- Planning, comparison, re-planning, complaints, and human approval.
- Customer and operator views plus auditable agent traces.

### Excluded

- Real booking, payment, refund, compensation, or supplier contracts.
- International visa, legal, medical, insurance, or safety advice.
- Guaranteed real-time price or availability.
- Complex group travel and fully autonomous high-risk decisions.

## Core data entities

Customer, TravelRequest, TransportOption, AccommodationOption, Activity, ItineraryVersion, SimulatedOrder, DisruptionEvent, Complaint, CompanyPolicy, HumanApproval, CustomerFeedback, AgentExecutionLog, and CostRecord.

## Evaluation plan

### User-value metrics

- Hard-constraint satisfaction and valid-plan completion rate.
- Time and effort required to obtain an acceptable plan.
- Customer acceptance, revision, and satisfaction rates in user testing.
- Complaint resolution clarity and perceived fairness.

### OPC feasibility metrics

- Cases handled without operator intervention.
- Operator minutes per planning case and complaint.
- Size and age of the human approval queue.
- Estimated model/tool cost per completed case.
- Percentage of cases escalated for the correct reason.

### Technical and safety metrics

| Metric | Initial target |
| --- | ---: |
| Hard-constraint satisfaction | ≥ 95% |
| Budget calculation accuracy | 100% |
| Conflict detection on the test set | 100% |
| Complaint routing accuracy | ≥ 90% |
| High-risk escalation | 100% |
| Unauthorised real/simulated refund execution | 0 |
| End-to-end task completion | ≥ 85% |

Testing will include unit tests, agent/tool integration tests, end-to-end business scenarios, tool/API failures, contradictory requirements, unavailable inventory, prompt injection, policy bypass attempts, and a limited single-agent versus multi-agent comparison.

## Development roadmap

### Phase 0 — User and business validation

- Interview potential travellers and identify the highest-cost planning/support problems.
- Define personas, customer journey, service promise, failure policy, and OPC feasibility hypotheses.
- Prioritise one connected scenario rather than attempting a full booking platform.

### Phase 1 — Requirements and modelling

- Finalise functional/non-functional requirements, assumptions, acceptance criteria, and traceability.
- Produce user requirement, feature, use-case, package, class, activity, state-machine, sequence, structured-class, and collaboration models.
- Model both the customer journey and operator workflow.

### Phase 2 — Planning MVP

- Implement structured intake, Travel Manager, Fare Planning, simulated transport data, hard constraints, three modes, alternatives, and explanations.

### Phase 3 — Complete service

- Add itinerary planning, accommodation/activities, budget/conflict tools, plan versions, simulated orders, Reviewer checks, and operator trace view.

### Phase 4 — Recovery and complaints

- Add weather/disruption events, impact analysis, re-planning, complaint state management, policy lookup, priority queue, and human approval.

### Phase 5 — Evaluation and demonstration

- Run normal, failure, adversarial, user-value, and OPC workload scenarios.
- Measure quality, completion, latency, cost, escalation, and operator effort.
- Reconcile implementation with Stage 1 models and prepare the final demonstration.

### Agile evidence throughout all phases

- Prioritised product backlog with requirement IDs and acceptance criteria.
- Sprint goals, task owners, estimates, and definition of done.
- Short stand-up notes, review outcomes, and retrospective actions.
- Feature branches, focused commits, peer reviews, and linked tests.
- A decision log for architecture changes and discarded choices.
- A contribution log generated from issues, models, code, tests, reviews, and presentation work.

### Future development

- Real transport, accommodation, map, calendar, and notification integrations.
- RAG for destinations, supplier terms, and company policies.
- PostgreSQL, background workers, events, monitoring, backup, and disaster recovery.
- Multi-city/group travel, multilingual support, voice, and mobile clients.
- Consent-based customer memory and preference portability.
- Operator analytics for demand, complaints, SLA, quality, and unit economics.
- Automated evaluation datasets, model routing, caching, and regression release gates.
- Supplier reliability scoring, disruption prediction, and proactive customer support.
- Business experiments for pricing, acquisition channels, partnerships, and retention.

## Planned repository structure

```text
.
├── README.md
├── README.zh-CN.md
├── docs/{business,requirements,architecture,models,agile}/
├── src/{agents,api,domain,tools,guardrails,data,ui}/
├── tests/{unit,integration,scenarios,evaluation}/
├── data/{transport,accommodation,activities,policies}/
└── pyproject.toml
```

## Three-person team plan

| Workstream | Primary owner | Responsibilities |
| --- | --- | --- |
| Customer operations | Member A | Customer Service, Complaint Agent, customer/operator UI, complaint states, user testing. |
| Planning and transport | Member B | Travel Manager, Fare Planning, scoring modes, transport/budget tools, orchestration. |
| Itinerary and assurance | Member C | Itinerary/Disruption Agents, event data, Reviewer, tracing, evaluation, system tests. |

Architecture decisions, integration, business validation, report review, presentation, and demonstration are shared. Contributions should be evidenced through issues, commits, reviews, models, and test ownership.

Before Stage 1 submission, the placeholders below must be replaced with actual names and verified contributions:

| Member | Requirements/models | Implementation/tests | Presentation/operations | Evidence links |
| --- | --- | --- | --- | --- |
| Member A — TBD | Customer and complaint requirements/models | Customer Service, Complaint, UI, user tests | Customer journey and complaint demo | Issues/commits/models — TBD |
| Member B — TBD | Planning and orchestration requirements/models | Manager, Fare Planning, scoring/tools | Architecture and travel-mode demo | Issues/commits/models — TBD |
| Member C — TBD | Itinerary, disruption, quality requirements/models | Itinerary, Disruption, Reviewer, evaluation | Testing, Agile evidence, disruption demo | Issues/commits/models — TBD |

## Demonstration story

1. A customer requests a Sydney–Melbourne trip in Value mode.
2. The system produces a checked itinerary and explains its evidence and trade-offs.
3. The customer switches to Comfort mode and compares the new version.
4. A simulated weather event cancels an outdoor activity.
5. TripMate AI proposes a checked alternative and reports the cost difference.
6. The customer complains that the replacement provides lower value.
7. The Complaint Agent investigates the order, original evidence, trace, and policy.
8. A proposed refund enters the operator approval queue.
9. The operator decides, Customer Service explains the outcome, and feedback is recorded.

This story demonstrates user value, company operations, LLM perception, agent delegation, deterministic tools, adaptation, complaint handling, and human accountability.

## Contributing

- Create or link a GitHub Issue for each meaningful change.
- Keep feature branches scoped to one requirement or component.
- Update tests and models when behaviour changes.
- Review changes before merging and record acceptance evidence.
- Never commit API keys, real customer data, or payment information.

## Course and legal notice

TripMate AI is an ELEC5620 Group 6 educational proof of concept. It is not a commercial booking service and must not be relied on for real travel, financial, legal, medical, immigration, or safety decisions.

No licence has been selected. Until one is added, all rights remain with the repository owners.
