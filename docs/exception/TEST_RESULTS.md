# Customer Exception prototype validation

**Latest (15 October):** see [integration acceptance](INTEGRATION_ACCEPTANCE.md):
238 repository tests, 38 focused Exception tests, the integrated Operations browser flow,
and two repeated fresh-data scenario sets. The original 13 October results below are retained
as historical evidence for PR #14 and its standalone scope.

Date: 13 October 2026 (Australia/Sydney). Local base: main commit `a1605f4`.
Execution environment: macOS, Python 3.14, local SQLite, synthetic data only.

- Full repository suite: **106 tests passed**, including **18 Exception tests**.
  Repeated before PR submission: 106 tests passed in 16.921 seconds. HTTP tests
  needed permission to bind temporary loopback ports; the initial restricted
  run failed at socket binding rather than an application assertion.
- Existing shared contract examples: **20 validated**. This checks structure,
  not business feasibility or human approval.
- Both CLI examples executed successfully: recovery stored 34 trace events;
  complaint stored 33 trace events.
- Browser checks with isolated Chrome: both buttons, conflict-to-human path,
  approval-pending path, reload and history restoration passed.
- Desktop (1440 px) and mobile (390 px) layouts inspected. No horizontal overflow
  or JavaScript page errors in the exercised flows.
- JavaScript syntax and Git whitespace checks passed.
- Final English workbench check: both normal demo buttons returned saved
  successful proposals, visible page text contained no Chinese characters,
  and the current viewport had no horizontal overflow. Screenshot:
  [English demonstration](screenshots/english-demo.png).

The tests execute rejection paths for budget, availability, expired evidence,
unsupported constraints, original schedule mismatch, transfer allowance,
unsupported/missing policy evidence, unavailable dependencies, incorrect review
version, persistence failure and mode/access guards. Persistence failure returns
FAILURE without a saved result, proposal release or fabricated approval reference.

Verification used no live model, no real supplier/payment integration, and no
Supabase writes. Real Operations/Reviewer/Supabase integration remains future work.
Team review, merge and production deployment remain pending. Delivery branch:
`codex/customer-exception-agent`, targeting `main`. Jira evidence mapping is
recorded in [JIRA_BACKLOG.md](JIRA_BACKLOG.md).
