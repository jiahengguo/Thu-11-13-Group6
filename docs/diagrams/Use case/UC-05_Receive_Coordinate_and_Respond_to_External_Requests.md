# UC-05: Receive, Coordinate, and Respond to External Requests

## Identification

- **Author:** Jiaheng Guo
- **Use Case ID:** UC-05
- **Level:** User Goal
- **Primary Requirement ID:** OPS-02
- **Related Requirement ID:** OPS-03
- **Related Use Case:** UC-07
- **Related Ad Hoc Diagram ID:** OPS-Ad_Hoc
- **Overall Use Case Diagram ID:** G-03

## Goal

To receive requests from customers and Travel Service Providers through one controlled interface. The Operations Agent confirms the required information, coordinates the appropriate handler, and delivers an approved and traceable response.

## Actors

### Primary Actors

- Customer
- Travel Service Provider

### Supporting Actors and Systems

- Travel Planning Agent
- Customer Exception Agent
- Supplier Partnership Agent
- Human Founder/Operator
- Authentication and Access Control mechanism
- Entitlement Service through UC-07
- Scheduled Case Review mechanism

## Trigger

A customer or Travel Service Provider submits a new operational request or follow-up message through the controlled external interface.

A Campaign Response may also trigger UC-05. It is recorded as the request source rather than the business intent.

## Preconditions

1. The controlled external interface is available.
2. Request categories, required fields, routing rules, confidence thresholds, and approval rules are configured.
3. The Operations Agent can access the Case Repository, Approved Service Information, and Agent Trace.
4. Authentication and access control are available for protected processing.
5. Access must be verified before an existing or Archived Case is read.
6. Specialist availability is not a precondition. Unavailability follows an error scenario.

## Success Conditions

- An approved response is delivered through the Operations Agent.
- The result, delivery, decisions, and required trace events are recorded.
- The Case closes with `Response Delivered`.

## Failure Conditions

Failure occurs when identity cannot be verified, information remains unconfirmed, classification remains unresolved, a required resource is unavailable, a response fails review, approval is rejected or pending, or delivery fails.

A failure does not automatically close the Case. The Case remains in a safe waiting state or is sent to Human Assistance.

## Main Success Scenario

1. A customer or Travel Service Provider submits an operational request.
2. The Operations Agent identifies the requester type and request source.
3. The system creates a `Draft CustomerCase` or `Draft SupplierCase`.
4. The system records the identity status as `Unverified`.
5. The requester completes the required identity and access checks.
6. The LLM identifies the intent and returns extracted fields, missing fields, unresolved questions, and classification confidence.
7. Deterministic rules load the required fields for the identified request type.
8. The Operations Agent asks focused questions until the required information is complete.
9. The Operations Agent presents the structured request to the requester.
10. The requester confirms the information.
11. The Case enters `Confirmed`.
12. Routing Rules select the responsible specialist Agent.
13. The hand-off and supplied information are recorded in the Agent Trace.
14. The Case enters `In Coordination`.
15. The specialist returns its findings, evidence, unresolved issues, and proposed response.
16. The Operations Agent checks the proposed response.
17. Required Human Approval is obtained.
18. The Case enters `Ready to Respond`.
19. The Operations Agent sends the response through the controlled interface.
20. The system confirms delivery, records the result, and closes the Case with `Response Delivered`.

## Alternative and Error Scenarios

### A1 - Anonymous enquiry

Anonymous users may receive application-function information from Approved Service Information. Business, Case, membership, or supplier processing requires identity verification.

### A2 - Verification failure

The Case remains `Draft`. Protected information is not accessed or disclosed. Human Assistance may help restore verification but cannot bypass access controls.

### A3 - Missing information

The Operations Agent asks focused questions. The Case cannot be sent to a specialist until the required information is complete and confirmed.

### A4 - Low classification confidence

If `classificationConfidence < configuredThreshold`, the Operations Agent asks for clarification. If uncertainty remains, the Case is sent to Human Assistance.

### A5 - Multiple independent intents

The Operations Agent proposes related Cases. They are created and routed only after the requester confirms the split.

### A6 - Repeated human request

Each explicit request increases `humanRequestCount`. When `humanRequestCount >= 2`, the Case is sent to Human Assistance even if information is incomplete.

### A7 - Confirmed information changes

Only changed fields normally require confirmation. A change to category, routing, risk, or approval conditions requires confirmation of the complete summary.

### A8 - Specialist requires more information

The Case enters `Awaiting Requester`. The specialist cannot directly contact the external requester. The Operations Agent obtains the missing information and returns the confirmed update to the specialist.

### A9 - Specialist is unavailable

The Case remains open. The failure is recorded and sent to Human Assistance. The Case is not reassigned without an authorised routing rule.

### A10 - Proposed response fails review

No external message is sent. The proposal returns to the specialist with a revision reason.

### A11 - Human Approval is required

The Case enters `Awaiting Human Approval`.

- `Approve`: continue to delivery.
- `Edit`: store the human revision and perform the final sending checks.
- `Reject`: do not send the proposal.
- `Take Over`: the human controls the content, but the Operations Agent remains the sending interface.

### A12 - Urgent request

The Case receives high priority. The response check may be expedited but cannot be skipped. Specialist Agents still cannot communicate directly with external actors.

### A13 - Delivery failure

The Case remains open in `Ready to Respond`. The failure is recorded and retried according to configuration. Persistent failure is sent to Human Assistance.

### A14 - Requester withdrawal

After the withdrawal is confirmed, the Case closes with `Requester Withdrawn`.

### A15 - Requester inactivity

Open Cases in `Awaiting Requester` are checked every 30 days. A Case with more than 30 calendar days since `lastRequesterResponseAt` is reported once to Human Assistance. It is not automatically closed or archived.

The Human Founder/Operator may continue waiting or archive the Case.

### A16 - Reply to an Archived Case

After identity and access verification, the Operations Agent reads the authorised archive and creates a linked Draft branch Case. The Archived Case remains read-only. The new Case does not inherit `humanRequestCount`.

## Business Rules

1. The Operations Agent is the only controlled external communication gateway.
2. Protected processing requires identity and access verification. Anonymous users may receive application-function information only.
3. A Case cannot be handed to a specialist before required information is complete and confirmed.
4. The LLM may classify, extract, and explain information. It cannot make identity, membership, contractual, financial, refund, or compensation decisions.
5. Low-confidence classification follows `classificationConfidence < configuredThreshold`.
6. `humanRequestCount >= 2` requires Human Assistance.
7. Specialist results require Operations review. Restricted commitments require Human Approval.
8. Inactive Cases are reported to a human and are not closed or archived automatically. Archived replies create new linked branch Cases.
9. Confirmations, tool results, routing, decisions, messages, hand-offs, and state changes must be recorded in the Agent Trace.

## Tools and Data

- Controlled External Interface
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

Human Approval is required before releasing:

- contracts or supplier agreements;
- binding prices or commercial terms;
- real financial spending;
- refunds or compensation;
- advertising or other external publications;
- restricted access decisions; or
- other legal, financial, or public commitments.

Routine acknowledgements, clarification questions, and factual status updates may be sent without Human Approval if they pass the routine communication check.

## Acceptance Criteria

### AC-UC05-01 - Access control

Given an anonymous requester, when a request is received, then the Operations Agent provides application information only. Protected processing requires verified identity and access.

### AC-UC05-02 - Draft and confirmation

Given a business request, when intake begins, then the system creates a Draft CustomerCase or SupplierCase. It cannot be sent to a specialist until required information is complete and confirmed.

### AC-UC05-03 - Classification and split

Given an ambiguous or multi-intent request, when the Operations Agent processes it, then it asks for clarification and obtains confirmation before splitting or routing the Case.

### AC-UC05-04 - Human Assistance

Given unresolved low confidence or `humanRequestCount >= 2`, when the escalation rule is evaluated, then the Case is sent to Human Assistance with the available information and reason.

### AC-UC05-05 - Routing

Given a confirmed Case, when Routing Rules are applied, then it is sent to the responsible specialist or UC-07 according to its confirmed intent.

### AC-UC05-06 - Controlled response

Given a specialist result, when the response check fails, then no external message is sent and the proposal returns for revision.

### AC-UC05-07 - Human Approval

Given a restricted commitment, when Human Approval is absent, then the external response remains paused.

### AC-UC05-08 - Delivery and trace

Given an approved response, when delivery succeeds, then the Operations Agent records the response and closes the Case. Failed delivery leaves it open.

### AC-UC05-09 - Inactive Case

Given a Case awaiting the requester for more than 30 days, when the scheduled review runs, then it is reported once to Human Assistance and is not automatically closed or archived.

### AC-UC05-10 - Archived Case reply

Given an authorised reply to an Archived Case, when it is processed, then the system creates a linked Draft branch Case. The archive remains read-only, and `humanRequestCount` is not inherited.

## G-03 Use Case Diagram Alignment

- UC-01 to UC-07 conditionally extend UC-05 according to the confirmed intent.
- Advertising Channel is associated with UC-08 and UC-05.
- The UC-05 association represents forwarding a source-tagged Campaign Response.
- UC-08 and UC-05 do not use a direct plain association.
- G-03 uses the complete TripMate AI system boundary.
- Internal business Agents remain inside that boundary.
