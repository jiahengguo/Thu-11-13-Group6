# UC-07: Enforce Membership and Premium Access

## Identification

- **Author:** Jiaheng Guo
- **Use Case ID:** UC-07
- **Primary Requirement ID:** OPS-03
- **Related Requirement IDs:** OPS-02, PLAN-01, PLAN-02, SUP-02
- **Related Use Cases:** UC-01, UC-05, UC-06, UC-08
- **Related Ad Hoc Diagram ID:** OPS-Ad_Hoc
- **Overall Use Case Diagram ID:** G-03

## Use Case Summary

| Template Field | UC-07 Definition |
| --- | --- |
| **Name** | Enforce Membership and Premium Access |
| **Goal** | Use verified membership status, trip counts, plan facts, and feature entitlements to make an allowed, denied, or pending decision that is explained and traceable. |
| **Level** | Supporting User Goal |
| **Precondition** | UC-05 has produced a confirmed request with the required subject and request data; the Membership Repository, Entitlement Catalogue, Plan Repository, policy rules, and Agent Trace are configured. |
| **Success Condition** | The current entitlement decision and its evidence are recorded; an allowed request proceeds, or a denied request returns a specific reason and permitted next action. |
| **Failure Condition** | The requested protected action remains blocked or pending when membership evidence, applicable rules, or approval cannot be verified. |
| **Trigger** | The Operations Agent requests an initial access check, a post-planning membership review, an expiry or downgrade action, or a feature/offer eligibility check. |

> **Scope:** UC-05 owns intake, classification, routing, and the controlled external response. UC-01 owns itinerary construction and calculation of plan facts. UC-06 or the relevant purchasing process owns quotation and price validation. UC-08 owns campaign and member-offer design. UC-07 only evaluates and records membership and entitlement decisions.

## Actors

### Primary Actor

- Operations Agent

### Affected External Actors

- Tourist
- Free Member
- Paid Member

### Supporting Actors and Systems

- Travel Planning Agent through UC-01
- Supplier Partnership Agent through UC-06 and UC-08
- Human Founder/Operator
- Authentication and Access Control mechanism
- Membership and Subscription Service
- Entitlement and Policy Rules
- Scheduled Membership Review mechanism

## Main Success Scenario

1. UC-05 confirms a request that requires travel planning, plan activation, a protected feature, or a member offer, and the Operations Agent invokes UC-07.
2. UC-07 identifies the subject, requested operation, and related CustomerCase.
3. The system retrieves the verified identity status, current membership record, confirmed subscription transaction, plan counts, and applicable entitlements.
4. Deterministic rules classify the subject as `Tourist`, `Free Member`, or `Paid Member` and create a timestamped entitlement snapshot.
5. UC-07 checks the requested operation against the subject's current quota, feature entitlement, applicable offer eligibility, and policy version.
6. The initial decision is recorded as `Allowed`, with the applicable limits and evidence.
7. For a travel-planning request, UC-05 routes the prepared request to UC-01.
8. UC-01 returns the Plan Version and standardised plan facts, including its status, duration-policy result, and relevant dates; UC-07 does not recalculate or modify the itinerary.
9. The Operations Agent invokes UC-07 for a post-planning review.
10. UC-07 retrieves the latest membership state and rechecks the Plan Version, current Draft and Planned/Active counts, and requested entitlements.
11. UC-07 records the final decision, membership snapshot, matched rules, Plan Version, explanation, and permitted next action in the Agent Trace.
12. An allowed Plan Version returns to UC-05 for the controlled response or permitted state transition.

## Alternative and Error Scenarios

### A1 - A Tourist requests travel planning

A Tourist may use UC-01 and retain at most two Draft Plans. The Draft cannot enter `Planned` until the user becomes an eligible member and UC-07 passes a new post-planning review.

### A2 - A Tourist or Free Member reaches the Draft limit

If two unexpired Draft Plans already exist, UC-07 denies creation of a third Draft and returns the existing Draft identifiers, last-modified times, and expiry times. The user must archive one Draft before retrying; the system does not automatically replace a Draft.

### A3 - A Free Member reaches the formal-plan limit

A Free Member may have at most two Plans whose status is `Planned` or `Active`, excluding grandfathered Active Plans covered by A9. UC-07 denies an additional transition to `Planned` and explains which Plans consume the quota.

### A4 - A plan fails an applicable membership rule

UC-01 supplies the calculated plan facts and applicable duration-policy result. UC-07 denies the requested state transition, records the matched membership rule, and returns revision options to UC-05. Plan dates and itinerary contents can only be revised through UC-01.

### A5 - A Paid Member requests unrestricted planning capacity

A Paid Member is not subject to Tourist or Free Member quantity and trip-duration entitlements. Each Draft still expires five calendar days after its last modification. Safety, availability, legal, supplier, and other non-membership controls remain applicable.

### A6 - A protected or Premium Feature is requested

UC-07 checks the Feature ID against the Entitlement Catalogue. `Interactive Route Map` is a Paid-only Feature. A configured temporary or targeted entitlement may also allow access if its scope and validity period match the request.

### A7 - Membership evidence or a rule service is unavailable

UC-07 returns `Pending Verification`, does not activate a Plan or Premium Feature, preserves the existing Draft and Case, records the failure, and schedules a retry. It does not misreport temporary verification failure as ineligibility. UC-05 sends the Case to Human Assistance when its mandatory escalation condition is met.

### A8 - Membership changes during planning

The post-planning review uses the latest verified membership state rather than the initial snapshot. UC-07 records both snapshots and the reason for any changed decision. Previous benefits are not automatically preserved unless a scoped Human Exception applies.

### A9 - Paid Membership approaches expiry or downgrades

The system notifies the user seven calendar days before downgrade and asks the user to select up to two Planned Plans and, when required, up to two Draft Plans to retain. At `00:00 Australia/Sydney` on `purchaseDate + purchasedTermDays + 1`, the account becomes a Free Member. If the user made no selection, the system retains the two Planned Plans with the nearest future departure dates, breaking a tie by the latest `lastModifiedAt`; other Planned Plans become `Archived due to membership downgrade`. For excess Draft Plans, it retains the two most recently modified unexpired Drafts and archives the remainder. Paid-era Active Plans remain Active and do not consume the later Free Member quota.

### A10 - A product is purchased within a grandfathered Active Plan

A confirmed transaction retains the membership price valid at its confirmation time and is never retrospectively repriced. A new or unconfirmed hotel, ticket, rental-car, or other product after downgrade uses the current Free Member entitlement and price. UC-07 supplies the timestamped membership snapshot; UC-06 or the relevant purchasing process calculates and validates the price.

### A11 - An archived Plan is requested after repurchase

Repurchasing Paid Membership does not automatically restore archived Plans. The user selects a Plan, UC-01 revalidates dates, availability, price, and feasibility, and UC-07 checks the new entitlement. Only a Plan that passes both checks returns to `Planned`; all archive and restoration records remain traceable.

### A12 - A commercial advertisement or member offer is evaluated

Tourists and Free Members may receive clearly labelled commercial advertising; Paid Members do not. Free and Paid Members may qualify for member offers, including Paid-only offers, according to the approved UC-08 campaign rules. UC-07 returns only `eligible` or `ineligible`, the applicable tier, and the decision basis; it does not promise a discount or design, approve, or publish a campaign.

### A13 - Payment or subscription confirmation fails

UC-07 does not activate Paid Membership without a confirmed transaction. An Agent may diagnose the failure, validate inputs, recommend another method, or authorise a compliant retry, but cannot convert a failed payment into a successful one. Repeated failures, anomalous transactions, refunds, and fee disputes follow the relevant process; refund disputes require Human review.

### A14 - The user disputes a decision or requests a human

A clear rule-based denial returns an explanation and does not automatically use Human Assistance. Data conflict, unresolved uncertainty, or the UC-05 mandatory escalation condition sends the Case to the Human Founder/Operator with the original evidence and decision.

### A15 - A Human Exception is approved

The Human Founder/Operator may correct membership data or approve a reasoned exception. The exception must identify its Case, Plan Version, Feature, or transaction scope; have an expiry time; be revocable; and record the original decision, new decision, reason, operator, and timestamps. It cannot silently or permanently change the global membership policy.

### A16 - UC-08 or an operator requests an additional entitlement

UC-08 may invoke an already approved entitlement mechanism for a campaign. A new or permanent Feature entitlement requires Human Approval and a controlled Entitlement Catalogue update. UC-07 consumes the resulting grant but does not create policy on its own.

### A17 - A Draft expires

Every Draft, including a Paid Member Draft, expires five calendar days after `lastModifiedAt`. The Draft enters `Expired`, stops consuming an active Draft quota, and remains available as read-only audit evidence.

## Business Rules

1. UC-05 owns request intake, routing, and external communication; UC-07 owns membership and entitlement decisions.
2. The three access states are `Tourist`, `Free Member`, and `Paid Member`.
3. A Tourist may retain at most two unexpired Draft Plans and cannot transition a Draft to `Planned`.
4. A Free Member may retain at most two unexpired Draft Plans and two Plans in `Planned` or `Active`, except for grandfathered Active Plans created during a valid Paid Membership.
5. A Paid Member has no membership-based Plan quantity or trip-duration limit. Non-membership controls still apply.
6. Every Draft expires five calendar days after its last modification, regardless of membership tier.
7. UC-01 calculates itinerary dates, duration, and feasibility; UC-07 consumes its standardised plan facts and applicable membership-policy result without modifying the itinerary.
8. The Operations Agent's LLM may identify the requested capability and explain a result, but deterministic Entitlement and Policy Rules make the access decision. The LLM cannot guess, calculate, or override an entitlement.
9. Paid Membership terms are 30, 90, 180, or 360 days. The purchase day is day zero; downgrade occurs at `00:00 Australia/Sydney` on `purchaseDate + purchasedTermDays + 1`.
10. The user is notified seven calendar days before Paid Membership downgrade and may choose the Plans to retain.
11. Grandfathered Active Plans survive downgrade and do not consume the Free Member formal-plan quota. New transactions after downgrade use the current Free Member entitlement.
12. Transaction pricing uses the verified membership snapshot at confirmation time. Confirmed transactions are not retrospectively repriced.
13. Paid Members receive no commercial advertising. Tourist and Free Members may receive clearly labelled commercial advertising.
14. Free and Paid Members may qualify for UC-08 member offers. UC-07 decides eligibility but does not determine the offer value.
15. `Interactive Route Map` is Paid-only unless a valid approved entitlement grant applies. Other Premium Features are identified through the Entitlement Catalogue.
16. UC-07 does not process payments, refunds, or subscription transactions and cannot activate Paid Membership without a confirmed transaction.
17. A temporary verification failure produces `Pending Verification`, not `Denied`, and protected operations remain blocked until verification or an authorised Human Exception.
18. A Human Exception must be scoped, time-limited, reasoned, revocable, and fully audited. A permanent policy change requires a controlled Entitlement Catalogue update.
19. Each decision records the subject, request, phase, membership snapshot, current counts, outcome, matched rule and version, explanation, timestamp, related Case and Plan Version, and any Human Exception.

## Tools and Data

- Authentication and Access Control mechanism
- Membership Repository
- Confirmed Subscription Transaction
- Membership and Subscription Service
- Plan Repository
- Draft Expiry Scheduler
- Scheduled Membership Review mechanism
- Entitlement Catalogue
- Entitlement and Policy Rules
- Member Offer Eligibility supplied by UC-08
- Plan Facts and Duration-policy Result supplied by UC-01
- Membership Snapshot supplied to UC-06 or the relevant purchasing process
- Notification Service
- Archive Store
- Agent Trace
- Human Assistance Queue
- Human Approval and Exception Record

## Approval Conditions

Human Approval is required for a scoped membership exception, correction of protected membership data, a new or permanent Feature entitlement, a global entitlement-policy change, and a refund or fee dispute referred from the relevant process.

Routine deterministic entitlement decisions, expiry processing under an approved policy, reminders, and use of an already approved UC-08 entitlement mechanism do not require case-by-case Human Approval.

## Acceptance Criteria

### AC-UC07-01 - Initial access decision

Given a confirmed UC-05 request, when the Operations Agent invokes UC-07, then the system records an `Allowed`, `Denied`, or `Pending Verification` decision with the current membership snapshot, matched rule, explanation, and related CustomerCase.

### AC-UC07-02 - Tourist and Free Draft quota

Given a Tourist or Free Member with two unexpired Draft Plans, when a third Draft is requested, then UC-07 denies creation, identifies the two quota-consuming Drafts, and requires the user to archive one before retrying.

### AC-UC07-03 - Free formal-plan quota

Given a Free Member with two quota-consuming Plans in `Planned` or `Active`, when another Draft requests transition to `Planned`, then UC-07 denies the transition and identifies the quota-consuming Plans; grandfathered Active Plans are excluded.

### AC-UC07-04 - Post-planning review

Given UC-01 returns a Plan Version and standardised plan facts, when UC-07 performs the post-planning review, then it uses the latest verified membership state, records the Plan Version and rule evidence, and does not recalculate or modify the itinerary.

### AC-UC07-05 - Draft expiry

Given any Draft reaches five calendar days after `lastModifiedAt`, when the expiry process runs, then the Draft enters `Expired`, no longer consumes Draft quota, and remains in the audit record.

### AC-UC07-06 - Paid Membership expiry and reminder

Given a confirmed Paid Membership term, when the reminder date is reached, then the system notifies the user seven calendar days before downgrade; when `purchaseDate + purchasedTermDays + 1` begins in Australia/Sydney, then the account becomes a Free Member and the transition is traced.

### AC-UC07-07 - Downgrade retention

Given a downgrading Paid Member has excess Plans and makes no selection, when downgrade processing completes, then the two Planned Plans with the nearest future departure dates are retained, ties use latest modification time, excess Drafts retain the two most recently modified unexpired items, the remainder are archived, and all Paid-era Active Plans remain quota-exempt.

### AC-UC07-08 - Transaction-time pricing status

Given a Paid-era Active Plan survives downgrade, when a product transaction is evaluated, then UC-07 supplies the membership snapshot valid at confirmation time; previously confirmed purchases retain their original status and new purchases use the current Free Member status.

### AC-UC07-09 - Premium Feature and offer eligibility

Given a Feature ID or approved UC-08 member offer, when eligibility is checked, then UC-07 returns the applicable tier, `eligible` or `ineligible`, and the decision basis; a Paid Member receives no commercial advertisement and `Interactive Route Map` remains Paid-only unless a valid grant applies.

### AC-UC07-10 - Verification failure

Given required membership evidence or a rule service is unavailable, when UC-07 evaluates a protected request, then it returns `Pending Verification`, preserves the Case and Draft, blocks the protected action, records the failure, and follows UC-05 escalation rules.

### AC-UC07-11 - Human Exception

Given an authorised Human Exception, when UC-07 applies it, then the record contains the original decision, replacement decision, scope, reason, operator, start and expiry times, and revocation status before access is allowed.

### AC-UC07-12 - Archived Plan restoration

Given a user repurchases Paid Membership and selects an archived Plan, when restoration is requested, then the Plan returns to `Planned` only after UC-01 revalidation and a successful UC-07 entitlement review, with both results traced.

## G-03 Use Case Diagram Alignment

- UC-07 conditionally extends UC-05 when a confirmed intent requires a membership, quota, Premium Feature, or member-offer decision.
- UC-05 remains responsible for intake, specialist routing, and the controlled external response.
- UC-01 supplies plan facts to UC-07 for the post-planning review; UC-07 does not own itinerary generation.
- UC-06 or the relevant purchasing process consumes the UC-07 membership snapshot for price validation.
- UC-08 supplies approved offer and temporary-entitlement rules; UC-07 only evaluates eligibility.
- Human Founder/Operator participates only for escalation, protected data correction, scoped exception, or controlled entitlement-policy change.
- All business Agents and entitlement services remain inside the TripMate AI system boundary.
