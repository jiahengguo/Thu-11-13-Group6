# UC-07: Enforce Membership and Premium Access
**Owner / Author:** Jiaheng Guo  
**Related requirements:** OPS-03, OPS-AH-01  
**Related diagrams:** AD-01, SD-01, SM-01, G-03

**Name:** Enforce Membership and Premium Access

**Goal:** Use verified membership status, trip facts, and feature entitlements to return an explained and traceable access decision for a protected TripMate AI action.

**Level:** Subfunction level

**Primary Actor:** Traveller

**Supporting External Actor:** Human Founder/Operator

**Internal Participants:** Operations Agent; Travel Planning Agent; Supplier Partnership Agent; Entitlement Service; Membership Repository; Entitlement Catalogue; Agent Trace

**Preconditions:**

- UC-05 has confirmed a request that requires a trip, plan, Premium Feature, or member-offer entitlement decision.

- The Operations Agent can access the customer, subscription, plan, and entitlement records.

- The membership, trip-count, trip-duration, advertising, feature-access, and member-offer eligibility rules are configured.

- The Agent Trace is available.

**Success Condition:** UC-07 records and returns `Allowed` or `Denied` with the verified membership status, applied rule, reason, and permitted next action. An allowed request continues through UC-05.

**Failure Condition:** If required membership evidence or the rule service is unavailable, UC-07 returns `VerificationFailed`, records the service failure, and blocks the protected action. Cases that meet the UC-05 escalation conditions are sent to Human Assistance.

**Trigger:** A Traveller requests creation or extension of a trip, activation of a Plan Version, access to a Premium Feature, or application of an approved member offer through the controlled Operations interface.

**Main Success Scenario**

1. UC-05 confirms a request that requires creation or extension of a trip, activation of a Plan Version, access to a Premium Feature, or application of an approved member offer.

2. The Operations Agent invokes UC-07 with the verified customer identifier, requested operation, trip dates when applicable, and related Case.

3. UC-07 retrieves the current membership status, active subscription evidence, Planned and Active trip count, and applicable feature or member-offer entitlements.

4. The deterministic Entitlement Service evaluates the request against the current Free Member or Paid Member rules.

5. UC-07 records the initial decision, membership snapshot, applied rule, and reason in the Agent Trace.

6. If travel planning is allowed, UC-05 routes the request to the Travel Planning Agent through UC-01.

7. UC-01 creates the Plan Version and returns its status, start date, end date, calculated calendar-day duration, and other required plan facts.

8. The Operations Agent invokes UC-07 for the post-planning review.

9. UC-07 retrieves the latest verified membership status and checks the Plan Version against the applicable trip-count, trip-duration, feature, and member-offer rules.

10. UC-07 records the final decision, applied rule, reason, and Plan Version.

11. UC-05 communicates the decision, reason, and permitted next action to the Traveller.

**Alternative and Error Flows**

**A1. Free Member trip-count limit is reached (at Steps 4 or 9)**

If the Free Member already has two simultaneous trips in `Planned` or `Active` status, UC-07 returns `Denied`, identifies the rule that failed, and preserves all existing trips. UC-05 explains that the Traveller may complete an existing trip or upgrade before trying again.

**A2. Free Member trip duration exceeds five calendar days (at Step 9)**

UC-01 supplies the start date, end date, and duration calculated as `end date - start date + 1 calendar day`. If the duration exceeds five calendar days, UC-07 returns `Denied`. UC-05 may offer the Traveller the valid choices of shortening the requested trip or upgrading; UC-07 does not change the itinerary.

**A3. Membership changes during planning (at Steps 8-9)**

UC-07 uses the latest verified membership status during the post-planning review. If it differs from the initial snapshot, UC-07 records both snapshots and evaluates the current request using the latest verified status.

**A4. Membership evidence cannot be verified (at Steps 3-4 or 9)**

UC-07 returns `VerificationFailed`, records the unavailable evidence or rule service, and blocks the protected action. The Case remains open under UC-05, which sends it to Human Assistance when its escalation conditions are met.

**A5. Premium Feature access is requested (at Steps 3-4)**

Interactive Route Map is available to active Paid Members. Other Premium Features are checked against the Entitlement Catalogue. If the membership or feature entitlement does not allow access, UC-07 returns `Denied` with the applied rule and next permitted action. UC-07 records and returns the decision through UC-05 without performing the trip-planning steps.

**A6. Advertising or an approved member offer is evaluated (at Steps 3-4)**

Commercial advertising shown to Free Members must be clearly labelled and must not affect hard-constraint filtering or recommendation ranking. Active Paid Members do not receive commercial advertising. For a member offer defined and approved through UC-08, UC-07 records and returns only the eligibility decision and applied membership level; it does not define the discount, calculate the quotation, or perform the trip-planning steps.

**A7. The Traveller disputes the decision (after Step 11)**

A deterministic denial is returned with its rule and explanation. Conflicting evidence, unresolved uncertainty, or the UC-05 mandatory escalation condition sends the Case to Human Assistance. UC-07 does not silently override the Entitlement Service.

**Business Rules**

1. A Free Member may hold no more than two simultaneous trips whose status is `Planned` or `Active`.

2. A Free Member trip may cover no more than five calendar days.

3. Trip duration is calculated as `end date - start date + 1 calendar day`.

4. Active Paid Members are not subject to the Free Member trip-count or trip-duration limits.

5. Active Paid Members receive an ad-free interface, Interactive Route Map access, and other approved Premium Features.

6. Advertising shown to Free Members must be clearly labelled and cannot alter hard-constraint filtering or recommendation ranking.

7. The Entitlement Service returns `Allowed`, `Denied` with a reason, or `VerificationFailed`.

8. UC-01 calculates itinerary dates, duration, and feasibility. UC-07 evaluates the returned plan facts without modifying the itinerary.

9. UC-08 defines an approved member-offer rule. UC-07 evaluates membership eligibility, while UC-06 applies the recorded discount to the applicable SupplierOffer and validates the selling price and margin.

10. The Operations Agent may use the LLM to identify the requested capability and explain the decision. Deterministic rules make the entitlement decision.

11. UC-07 does not process payments, refunds, subscription transactions, or itinerary changes.

12. UC-07 records the Case, Plan Version when applicable, membership snapshot, current trip count, decision, applied rule, reason, and timestamp in the Agent Trace.

**Tools and Data**

- Authentication and Access Control mechanism

- Customer and Membership Repository

- Plan Repository

- Entitlement Catalogue

- Entitlement and Policy Rules

- Plan facts supplied by UC-01

- Member offer rules supplied by UC-08

- Membership eligibility result supplied to UC-06

- Human Assistance Queue

- Agent Trace

**Acceptance Criteria**

**AC-UC07-01 - Initial entitlement check**

Given a confirmed request, when the Operations Agent invokes UC-07, then the system records and returns the current membership level, decision, applied rule, and reason.

**AC-UC07-02 - Free Member trip-count limit**

Given a Free Member with two simultaneous trips in `Planned` or `Active` status, when another trip requests activation, then UC-07 returns `Denied`, identifies the failed trip-count rule, and preserves the existing trips.

**AC-UC07-03 - Free Member trip-duration limit**

Given a Free Member Plan Version covering more than five calendar days, when UC-07 performs the post-planning review, then it returns `Denied` with the duration rule and does not modify the itinerary.

**AC-UC07-04 - Post-planning review**

Given a Plan Version returned by UC-01, when UC-07 performs the post-planning review, then it uses the latest verified membership status, current trip count, and calculated calendar-day duration and records whether the Plan may proceed.

**AC-UC07-05 - Premium Feature access**

Given a request for Interactive Route Map or another registered Premium Feature, when UC-07 checks the Entitlement Catalogue, then it returns the access decision, membership level, and entitlement used.

**AC-UC07-06 - Approved member offer**

Given an approved UC-08 member-offer rule, when eligibility is checked, then UC-07 returns the membership eligibility result and applied level without defining or changing the discount.

**AC-UC07-07 - Verification failure**

Given that membership evidence or the rule service is unavailable, when UC-07 checks a protected request, then it returns `VerificationFailed`, records the service failure, blocks the protected action, and follows the UC-05 escalation rules.
