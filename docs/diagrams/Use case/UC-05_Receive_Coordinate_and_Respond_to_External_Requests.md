# UC-05: Receive, Coordinate, and Respond to External Requests
**Owner / Author:** Jiaheng Guo  
**Related requirements:** OPS-02, OPS-AH-01  
**Related diagrams:** AD-01, SD-01, SM-01, G-03

**Name:** Receive, Coordinate, and Respond to External Requests

**Goal:** Receive an external request, confirm the required information, coordinate the responsible handler, and deliver an approved and traceable response.

**Level:** User-goal level

**Primary Actors:** Traveller; Travel Service Provider

**Supporting External Actor:** Human Founder/Operator

**Internal Participants:** Operations Agent; Travel Planning Agent; Customer Exception Agent; Supplier Partnership Agent; Entitlement Service; Reviewer/Guardrail; Authentication and Access Control mechanism; Agent Trace

**Preconditions:**

1. The controlled external interface is available.

2. Request categories, required fields, routing rules, and approval rules are configured.

3. The Operations Agent can access the Case Repository, Approved Service Information, Entitlement Service, and Agent Trace.

4. Authentication and access-control services are available.

**Success Condition:** The approved response is delivered through the Operations Agent, the processing and delivery records are stored in the Agent Trace, and the Case is closed.

**Failure Condition:** If the request cannot be verified, confirmed, coordinated, approved, or delivered, the Case remains open in the relevant waiting or escalation state.

**Trigger:** A Traveller or Travel Service Provider submits a new request or follow-up message through the controlled external interface. The request may be a source-tagged Campaign Response.

**Main Success Scenario**

1. The requester submits an external request.

2. The Operations Agent identifies the requester type and request source.

3. The system creates a Draft CustomerCase or SupplierCase.

4. The requester completes the required identity and access checks.

5. The Operations Agent uses the LLM to identify the request type and extract the available information.

6. Deterministic rules identify the required fields for the request type.

7. The Operations Agent obtains any missing information from the requester.

8. The requester confirms the structured request.

9. The system updates the Case to Confirmed.

10. Routing Rules assign the Case to the responsible specialist Agent or the Entitlement Service.

11. The Operations Agent records the hand-off and continues tracking the Case.

12. The responsible specialist returns its findings, evidence, and proposed response.

13. The Operations Agent checks the response against the confirmed request, available evidence, business rules, and approval status.

14. Human Approval is obtained when the response contains a restricted commitment.

15. The Operations Agent sends the approved response through the controlled external interface.

16. The system records the delivery and closes the Case.

**Alternative and Error Flows**

**A1. Routine enquiry (at Steps 5-10)**

If the request can be answered using Approved Service Information, the Operations Agent prepares and sends the response without specialist coordination.

**A2. Identity cannot be verified (at Step 4)**

The Case remains in Draft. Protected Case, membership, or supplier information is processed after verification is completed.

**A3. Required information is missing (at Steps 5-7)**

The Operations Agent asks focused questions and continues intake after the requester supplies the missing information.

**A4. Classification confidence is low (at Step 5)**

The Operations Agent asks the requester to clarify the intent. If the intent remains unclear, the Case is sent to Human Assistance.

**A5. The request contains multiple independent intents (at Steps 5-8)**

The Operations Agent proposes separate but related Cases. The Cases are created after the requester confirms the split.

**A6. Confirmed information changes (after Step 8)**

The Operations Agent updates the affected fields and obtains confirmation. If the change affects category, routing, risk, or approval conditions, the requester confirms the complete request summary again.

**A7. The specialist requires more information (at Step 12)**

The Case enters Awaiting Requester. The Operations Agent obtains and confirms the additional information before returning it to the specialist.

**A8. The specialist is unavailable (at Steps 10-12)**

The Case remains open and is sent to Human Assistance with the request details and recorded coordination failure.

**A9. The proposed response fails review (at Step 13)**

The Operations Agent returns the response to the responsible specialist with the revision reason.

**A10. Human Approval is required (at Step 14)**

The Case enters Awaiting Human Approval. The Human Founder/Operator may approve, edit, reject, or take over the response.

**A11. Delivery fails (at Steps 15-16)**

The Case remains Ready to Respond while delivery is retried. Persistent delivery failure is sent to Human Assistance.

**A12. The requester withdraws the request (at any step before closure)**

The withdrawal is recorded and the Case is closed as Requester Withdrawn.

**Business Rules**

1. The Operations Agent is TripMate AI’s controlled external communication gateway.

2. Protected processing requires verified identity and access.

3. Required information must be complete and confirmed before specialist coordination begins.

4. The LLM may classify requests, extract information, identify missing fields, and explain results.

5. Deterministic rules define required fields, membership entitlements, routing conditions, and approval requirements.

6. Planning and revision requests are routed to the Travel Planning Agent.

7. Disruptions and complaints are routed to the Customer Exception Agent.

8. Supplier cooperation, inventory, offer, and price-related requests are routed to the Supplier Partnership Agent.

9. Membership checks are handled through the Entitlement Service.

10. Specialist responses are reviewed by the Operations Agent before delivery.

11. Restricted financial, contractual, legal, access, refund, or compensation decisions require Human Approval.

12. If humanRequestCount >= 2, the Case is sent to Human Assistance.

13. Confirmations, classifications, tool results, routing decisions, hand-offs, approvals, responses, and closure events are recorded in the Agent Trace.

**Tools and Data**

- Controlled External Interface

- LLM Classification Output

- Authentication and Access Control mechanism

- Required Field Rules

- Routing Rules

- CustomerCase and SupplierCase Repository

- Approved Service Information

- Entitlement Service

- Specialist Findings and Proposed Responses

- Human Assistance Queue

- Human Approval Record

- Agent Trace

**Acceptance Criteria**

**AC-UC05-01 — Request intake**

Given an external request, when the Operations Agent begins intake, then a Draft CustomerCase or SupplierCase is created with the requester type and request source.

**AC-UC05-02 — Information confirmation**

Given a Draft Case, when all required information has been collected and confirmed by the requester, then the Case becomes eligible for routing.

**AC-UC05-03 — Routing**

Given a confirmed request, when Routing Rules are applied, then the Case is assigned to the responsible specialist Agent or Entitlement Service and the hand-off is recorded.

**AC-UC05-04 — Human assistance**

Given unresolved classification uncertainty or humanRequestCount >= 2, when the escalation rule is met, then the Case is sent to Human Assistance with its available information and escalation reason.

**AC-UC05-05 — Response control**

Given a proposed specialist response, when the Operations Agent reviews it, then only a response that satisfies the confirmed request, evidence, business rules, and approval conditions proceeds to delivery.

**AC-UC05-06 — Completion**

Given an approved response, when delivery succeeds, then the response and delivery result are recorded and the Case is closed.
