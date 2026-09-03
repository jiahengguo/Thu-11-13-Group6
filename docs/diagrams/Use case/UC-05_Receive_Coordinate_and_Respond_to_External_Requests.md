# UC-05: Receive, Coordinate, and Respond to External Requests

## Identification

- **Author:** Jiaheng Guo
- **Use Case ID:** UC-05
- **Primary Requirement ID:** OPS-02
- **Related Requirement ID:** OPS-03
- **Related Use Cases:** UC-07, UC-08
- **Related Ad Hoc Diagram ID:** OPS-Ad_Hoc
- **Overall Use Case Diagram ID:** G-03

## Use Case Summary

| Template Field | UC-05 Definition |
| --- | --- |
| **Name** | Receive, Coordinate, and Respond to External Requests |
| **Goal** | Receive an external request, confirm the required information, coordinate the responsible handler, and deliver an approved and traceable response. |
| **Level** | User Goal |
| **Precondition** | The controlled external interface, processing rules, Case Repository, Agent Trace, and access-control services are available. |
| **Success Condition** | The response is delivered, the processing record is complete, and the Case reaches `Response Delivered`. |
| **Failure Condition** | The Case remains open in the relevant waiting or escalation state when processing cannot be completed. |
| **Trigger** | A customer or Travel Service Provider submits a new request or follow-up message, including a source-tagged `Campaign Response`. |

> **Scope:** UC-05 receives a `Campaign Response` and records its source. UC-08 belongs to the Supplier Partnership Agent and covers supplier-data-based campaign planning, evaluation, budgeting, approval, and publication.

## Actors

### Primary Actors

- Customer
- Travel Service Provider

### Supporting Actors and Systems

- Advertising Channel
- Travel Planning Agent
- Customer Exception Agent
- Supplier Partnership Agent
- Human Founder/Operator
- Authentication and Access Control mechanism
- Entitlement Service through UC-07
- Scheduled Case Review mechanism

## Main Success Scenario

1. A customer or Travel Service Provider submits an operational request through the controlled external interface.
2. The Operations Agent identifies the requester type and request source.
3. The system creates a `Draft CustomerCase` or `Draft SupplierCase`.
4. The requester completes the required identity and access checks.
5. The Operations Agent identifies the intent and extracts the provided information.
6. Required Field Rules identify missing information, which the Operations Agent obtains from the requester.
7. The requester confirms the structured request.
8. The Case enters `Confirmed`.
9. Routing Rules select the responsible specialist Agent or UC-07, and the hand-off is recorded.
10. The specialist returns its findings, evidence, unresolved issues, and proposed response.
11. The Operations Agent reviews the response and obtains Human Approval when required.
12. The Operations Agent sends the response through the controlled external interface.
13. The system records delivery and closes the Case with `Response Delivered`.

## Alternative and Error Scenarios

### A1 - Identity is not verified

An anonymous requester receives application-function information. The Case remains `Draft` until identity and access are verified or Human Assistance is requested.

### A2 - Information or intent is unclear

The Operations Agent asks focused questions. Low-confidence classification is referred to Human Assistance if clarification does not resolve it. Multiple independent intents become related Cases after the requester confirms the split.

### A3 - The requester asks for a human

Each explicit request increments `humanRequestCount`. At `humanRequestCount >= 2`, the Case is sent to Human Assistance with the information collected so far.

### A4 - Confirmed information changes

The requester confirms the changed fields. Changes affecting category, routing, risk, or approval conditions require confirmation of the complete summary.

### A5 - Specialist coordination is interrupted

If more information is required, the Case enters `Awaiting Requester`. If the specialist is unavailable, the Case remains open and is referred to Human Assistance.

### A6 - Review or approval requires revision

A response that fails review returns to the specialist with the reason. A restricted commitment places the Case in `Awaiting Human Approval` until the Human Founder/Operator approves, edits, rejects, or takes over the response.

### A7 - Delivery does not complete

The Case remains `Ready to Respond` while delivery is retried. Persistent failure is referred to Human Assistance.

### A8 - The Case becomes inactive or is withdrawn

A Case in `Awaiting Requester` for more than 30 calendar days is reported once to Human Assistance for a continue-waiting or archive decision. A confirmed withdrawal closes the Case with `Requester Withdrawn`.

### A9 - The requester replies to an Archived Case

After access verification, the Operations Agent creates a linked Draft branch Case. The archive remains read-only, and the new Case starts with its own `humanRequestCount`.

## Business Rules

1. The Operations Agent is the controlled external communication gateway.
2. Protected processing requires verified identity and access.
3. Required information must be complete and confirmed before specialist coordination.
4. Identity, membership, contractual, financial, refund, and compensation decisions use the relevant deterministic rule or authorised human decision.
5. `classificationConfidence < configuredThreshold` starts clarification or escalation.
6. Specialist results require Operations review; restricted commitments require Human Approval.
7. Confirmations, tool results, routing, decisions, messages, hand-offs, and state changes are recorded in the Agent Trace.

## Tools and Data

- Controlled External Interface
- Campaign Response source metadata
- LLM Classification Output
- Authentication and Access Control mechanism
- Required Field Rules
- Configured Threshold Store
- Routing Rules
- OperationCase Repository
- Approved Service Information
- Agent Trace
- Specialist Findings and Proposed Responses
- Human Assistance Queue
- Human Approval Record
- Scheduled Case Review mechanism
- Archived Case Store
- Entitlement Service through UC-07

## Approval Conditions

Human Approval is required when a response contains a contract, binding commercial term, financial commitment, refund, compensation, restricted access decision, or other legal or public commitment.

Routine acknowledgements, clarification questions, and factual status updates follow the routine communication check.

## Acceptance Criteria

### AC-UC05-01 - Intake and confirmation

Given an external request, when intake is complete, then a Draft Case exists with a confirmed intent and all required information.

### AC-UC05-02 - Access control

Given protected processing, when the Case proceeds, then verified identity and access are recorded.

### AC-UC05-03 - Routing

Given a confirmed Case, when Routing Rules are applied, then the Case is assigned to the responsible specialist or UC-07 and the hand-off is traced.

### AC-UC05-04 - Escalation

Given unresolved low confidence, specialist unavailability, or `humanRequestCount >= 2`, when the relevant rule is met, then the Case is sent to Human Assistance with its context and reason.

### AC-UC05-05 - Approval

Given a restricted commitment, when the response is ready, then its approval outcome is recorded before delivery.

### AC-UC05-06 - Completion

Given an approved response, when delivery succeeds, then the result is recorded and the Case reaches `Response Delivered`.

## G-03 Use Case Diagram Alignment

- UC-01, UC-02, UC-03, UC-04, UC-06, and UC-07 conditionally extend UC-05 according to the confirmed intent.
- Advertising Channel is associated with UC-08 and UC-05.
- UC-08 and UC-05 have no direct use-case association.
- All business Agents remain inside the TripMate AI system boundary.
