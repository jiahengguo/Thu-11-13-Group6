# Stage 2 Group Contribution Statement

**Group Number:** Thu 11-13 Group 6

## Contribution by assessment criterion

Enter each of the four members’ names and Student IDs in the corresponding column. For each assessment criterion, enter each member’s contribution percentage. The four percentages in every criterion row must add up to 100%.

| Assessment criterion | Member 1 | Member 2 | Member 3 | Member 4 | Row total |
| --- | --- | --- | --- | --- | --- |
| Student name | Jiaheng Guo | Runda Weng | Mo Shen | Jingao Yang | |
| Student ID | 510423614 | | 550394172 | 540157776 | |
| 1. Implementation of Stage 1 Requirements and Design (7 marks) | 25% | | 25% | 25% | **100%** |
| 2. Demonstrating AI Agent Capabilities (4 marks) | 30% | | 30% | 20% | **100%** |
| 3. Agile Development Experience (4 marks) | 40% | | 20% | 20% | **100%** |
| 4. Incorporation of Advanced Technologies (5 marks) | 60% | | 15% | 15% | **100%** |

## Specific work completed by each student

Describe each member’s specific tasks and deliverables. Add text as needed.

### Member 1 Jiaheng Guo

**Specific work completed:** 

Stage 1 requirements and Operations implementation: Implemented the Operations workflow for UC-05, including request intake, confirmation, clarification, specialist routing, case coordination, human assistance, controlled response delivery, and linked case histories and execution traces. Implemented the foundational UC-07 membership rules and access controls, including Free/Paid entitlement checks and trip limits. UC-07 was implemented collaboratively, with Moore contributing the later benefits presentation and itinerary-map functionality.

Shared contracts and agent integration: Defined shared agent contracts, domain schemas and requirement mappings. Connected authenticated Operations requests to the Planning and Exception modules, enabling reviewed itinerary presentation, explicit adoption and trip activation, disruption evidence collection, recovery recommendations, scoped human decisions, clarification and safe investigation resumption. Integrated the specialist implementations contributed by other team members into the authenticated portal workflow.

Portal and cloud infrastructure: Built the public website and separate Traveller, Supplier and Operator workspaces. Integrated Supabase registration, sign-in and account-recovery flows, backend role and ownership checks, protected sessions, and atomic persistence of Operations records and audit trails.

Model integration and reliability improvements: Connected the supplied course model to the integrated planning workflow and implemented bounded model proposals with deterministic validation feedback. Developed setup, startup and provider-readiness checks and repeatable demo-account preparation. Fixed installation, Operator delivery, cloud snapshot/JSON handling, timeout, version-conflict and interrupted-request issues identified during integration and acceptance work.

React and CI/CD: Migrated authenticated request queues to reusable React components, including search, filtering, selection retention and processing feedback. Implemented GitHub Actions regression checks across Linux and Windows, reproducible frontend builds, and automatic source ZIP delivery with checksums and provenance. Added ZIP extraction, repeated initialization and authenticated HTTP smoke checks, preserving a runtime that does not require Node/npm.

Agile collaboration and delivery evidence: Prepared and maintained Stage 2 Jira backlog descriptions, dependencies and implementation handoffs. Used branches and pull requests to deliver incremental changes, tracked and resolved integration defects, and documented setup instructions, supported demonstration scenarios, verification results and remaining limitations.

### Member 2

**Specific work completed:** [type here]

### Member 3

**Specific work completed:** [type here]

### Member 4 Jingao Yang

**Specific work completed:** 
Supplier Partnership implementation: Implemented the UC-06 supplier offer assessment workflow, covering offer intake, structured data extraction, availability and commercial-term validation, selling-price and minimum-margin checks, review, and version-linked human decisions. Reused the shared PricingService and independently validated its results. Preserved offer history and prevented expired, invalid, superseded or unapproved offers from being selected by other agents.

Agent integration and shared persistence: Implemented the SupplierGateway and shared-storage adapter to connect supplier assessment with authenticated Operations requests and Planning offer lookup. Provided current approved offer, price and source information for downstream use. Added checks for supplier ownership, current versions and approval authority, with traceable results and failure handling.

UC-08 campaign planning and AI capabilities: Implemented the campaign preparation, evaluation and approval workflow in the authenticated Operator portal. Integrated the shared model interface for constrained campaign drafting, while retaining deterministic checks for supplier evidence, simulated channel costs, budgets, dates and content restrictions. Bound approval, revision and rejection decisions to exact proposal versions and invalidated previous authority when campaign materials changed.

Member-benefit integration: Implemented versioned campaign member-offer rules, eligibility handoff to UC-07 and separate customer quotations through UC-06. Rechecked discounted margins, prevented discount stacking and preserved original supplier prices. Connected explicitly consented simulated campaign responses to Operations with campaign and source references.

Development tools and database reliability: Built the B02 local diagnostic workbench and B03 deterministic synthetic dataset, including repeatable scenarios, persistence checks and safe fixture reset. Investigated the Supabase shared-snapshot timeout and implemented a PostgreSQL function migration that removed observed temporary-storage spill while preserving snapshot contents and backend-only permissions. Documented comparative measurements and deployment verification.

Testing, release evidence and agile delivery: Added Supplier and campaign regression tests, boundary cases, labelled local browser evidence and implementation handoffs. Contributed four authenticated recovery-lifecycle scenarios and five release-evidence checks for WN5620-20/49, preventing empty or skipped test runs from being reported as successful acceptance. Recorded two consecutive isolated release runs totalling 200 passing test executions. Delivered changes through branches and pull requests, with requirement mappings, verification records and clear distinctions between simulated testing and real-provider acceptance.

