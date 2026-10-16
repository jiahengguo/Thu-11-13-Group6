# Customer Exception Agent prototype

**15 October integration update:** see [INTEGRATION.md](INTEGRATION.md) for the
new Operations workflow and [acceptance evidence](INTEGRATION_ACCEPTANCE.md).
The guide below describes the original standalone demonstration merged in PR #14;
its simulation/specialist-handoff limits do not describe the new opt-in integration.

Owner: Runda / wrd. Implements the confirmed specialist portion of EXC-01 / UC-03
and EXC-02 / UC-04. Based on the supplied **TripMate AI111.docx**, sections 2.4,
3.4, 6.3, UC-03/04, G-02 and the relevant AD-03/SD-03/SM-03 constraints. This is
an isolated simulation with real deterministic checks and durable local records.
No Word report edits are included.

Delivery branch: `codex/customer-exception-agent`, targeting `main`. See
[Jira backlog and report mappings](JIRA_BACKLOG.md) for WN5620-39–43 and their
existing parent tasks. The core module is `src/tripmate/exception_handling/`;
`src/tripmate/agents/exception.py` is the specialist entry point.

## Start and demonstrate

From the repository root, on macOS/Linux:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python -m tripmate.api.server --workbench --port 8766
```

Open **http://127.0.0.1:8766/#exception-panel**. On Windows use `py -3 -m venv .venv`
and `.venv\Scripts\python.exe` instead of `.venv/bin/python`.

The explicit `--workbench` flag is required: the default web entry is the team's
Supabase-authenticated portal. This demonstration needs no Supabase credentials
or model key. Run in `FIXTURE` mode (the default); `STUB` refuses both execution
and history. The development workbench is loopback-only. No hosted portal or
cloud database changes are part of this delivery.

1. Select **Standard case** and click **Investigate cancellation**. A synthetic cancelled flight
   has two replacement offers. The early flight passes and the late flight is
   excluded. The evaluated total is AUD 680, below the supplied AUD 800 ceiling.
   The proposed arrival is 60 minutes later than the original. Original hotel
   and activity selections are preserved, and downstream timing is checked.
2. Click **Investigate delay complaint**. Scheduled arrival 10:30 and recorded arrival 12:00
   establish a 90-minute delay. An explicitly simulated policy supports explaining
   the delay and offering an apology. No financial entitlement is inferred.
3. Select **Conflicting evidence**, then either button: the recorded conflict causes
   `HUMAN_ASSISTANCE`; no unsupported recommendation is released.
4. Select **Human approval required**: a version-scoped PENDING approval request is
   saved. There is no invented human decision, eligibility finding or refund amount.
5. Expand **Saved investigations**, reload or restart, and select a previous run.
   Full source references, checks, input snapshot, proposals, approvals and trace
   events remain available. B03 reset does not delete exception records.

Other selectable scenarios: missing evidence, no alternatives/policy, low
confidence, safety concern, unavailable dependency and failed review.

Command-line equivalents:

```sh
.venv/bin/python -m tripmate.exception_handling --case disruption
.venv/bin/python -m tripmate.exception_handling --case complaint
.venv/bin/python -m tripmate.exception_handling --case complaint --scenario conflict
.venv/bin/python -m tripmate.exception_handling --case complaint --scenario approval
```

CLI snapshots default to `data/exception-demo.sqlite3`; pass `--database` to
choose another file. Web snapshots use the configured `TRIPMATE_DATABASE_PATH`
(default `data/tripmate.sqlite3`), in the append-only `exception_runs` table.

## What executes and what is simulated

**Executed:** contract checks, case ownership/type/status binding, source identity
and reference checks, freshness and conflicts, evidence gates, Decimal cost sums,
time comparisons, unchanged-baseline enforcement, human-handling decisions,
version-bound simulated review, atomic persistence and UI/API handoff.

**Simulated:** already-confirmed Operations input and structured source records,
Supplier alternatives, Planning revision interface, rule-based Reviewer and
commercial policies. `executionMode=FIXTURE`, `modelExecution=NONE` and dependency
labels are retained in every saved run. No automatic production agent wiring is
performed; unconfigured `CustomerExceptionAgent()` remains an explicit stub.

`SUCCESS` means a checked, saved internal proposal, not a recovered booking or
resolved complaint. Every case remains open. Operations receives the result and
owns external review, human coordination and traveller communication. This module
has no outbound traveller, booking, payment, refund or compensation capability.

The prototype ends at the specialist handoff. EXC-O1, background notifications,
traveller choice, reminders/timeouts, real human decisions, actual transactions,
production auth integration and autonomous revision loops are outside this scope.
Failed review goes to human handling; corrected input may be manually rerun.

## Explicit example rules and limits

These are example inputs, **not additional report requirements**:

- Recovery supports one disrupted flight and later hotel/activity arrangements.
  The candidate must replace only that flight and preserve every other item.
- All four confirmed recovery constraints must be supplied: `budgetTotal`,
  `earliestDeparture`, `latestArrival`, `minTransferMinutes`. The fixture supplies
  AUD 800, 09:00, 14:00 and 60 transfer minutes. Extra or unsupported constraints
  cause human assistance, not silent relaxation. This is not a general multi-leg
  solver, accessibility/baggage validator or ranking algorithm.
- Total = already-paid non-refundable cost + all revised remaining costs.
  Example: 180 + 220 + 240 + 40 = AUD 680. No presumed refund/credit is deducted;
  input amounts are nonnegative AUD strings with two decimals. No percentage
  rounding/tie rule or compensation formula is introduced.
- Both examples use 20 October 2026 scenario clocks (08:00 recovery, 16:00 complaint).
  Freshness is evaluated at that supplied time; actual recording time is stored
  separately. Source expiry and offer validity are explicit fixture inputs.
- Evidence conflict detection compares structured assertions for the same key.
  The prototype does not authenticate external evidence or interpret arbitrary
  documents/free text. Qualitative confidence is supplied with the structured
  context; SUFFICIENT alone cannot bypass evidence checks. LOW/UNKNOWN escalates.
- Delay investigation requires referenced scheduled and actual arrival times;
  the schedule must match the affected baseline item. One explicit, versioned
  simulated policy is required. Missing/conflicting policies require clarification.
- Legal/safety and restricted-action flags are structured inputs. A future natural
  language intake adapter must reliably supply them; this version does not claim
  to detect every risk from free text.

## Interfaces and integration handoff

```python
from tripmate.agents.exception import CustomerExceptionAgent
from tripmate.exception_handling import ExceptionRuntime

runtime = ExceptionRuntime(context_source, repository, supplier, planning, reviewer)
result = CustomerExceptionAgent(runtime).handle_case(confirmed_case)
```

Shared v1 `Case`, `AgentResult`, `TraceEvent`, `Approval` and `SubjectRef` schemas
are unchanged. Module-local `ExceptionContext` is validated in `contracts.py` and
loaded by case ID rather than inserted into undeclared Case fields.

| Record | Contents |
| --- | --- |
| Case | Confirmed CUSTOMER DISRUPTION/COMPLAINT, Operations coordinator, Exception handler, ownership, correlation and sources |
| ExceptionContext | Matching case/traveller, scenario time, issue/risk flags, original itinerary, constraints, structured evidence, offers and policies |
| AgentResult | Findings, proposal reference, checks, errors, review, approval references and next action for Operations |
| Proposal | Recovery candidates/rejections and cost/time implications, or delay findings and cited policy; immutable subject/version |
| Saved snapshot | Complete input/context, result, proposal, pending approvals, source-linked trace, actual recording time and explicit simulation labels |

`ContextSource.load(case_id)`, `SupplierPort.alternatives(context)` and
`PlanningPort.revise(context, offer)` are replaceable ports. `review(subject,
evidence, policies)` uses the existing ReviewService calling convention. The
repository atomically saves all result/approval/trace data, and provides
`get(run_id)`, `recent()` and `find_by_case(case_id)`.

The team's Operations service accepts an injected specialist through
`operations.specialists['exception']`. Before integrating it, supply a real
confirmed-context adapter and subject/approval lookup adapters; reconcile shared
Reviewer and trace persistence. The current prototype explicitly accepts only
simulated sources. Do not enable it for arbitrary live portal cases or simply
relabel FIXTURE as REAL. No changes were made to the team's Supabase tables.

## Validation

```sh
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m tripmate --validate-examples docs/contracts/v1/examples
```

`tests/test_exception.py` covers normal recovery/complaint, conflicts, missing
sources, expired/future/unknown evidence, closed/withdrawn cases, cross-owner input,
unsupported constraints, budgets/availability/routes/downstream timing, malformed
planner output, review version mismatch, unavailable dependencies, pending approvals,
save failure, persistence across repository reopen, repeat-run isolation, HTTP
CSRF token checks, mode guards and reset retention.

Report mappings: UC03-01/02 investigation and candidates; UC03-03 and UC04-03
executed validation/review; UC03-04 and UC04-04 incomplete or uncertain handling;
UC03-05 and UC04-05 pending approval; UC03-06 and UC04-07 durable traces;
UC04-01/02 evidence and policy; UC04-06 documented internal human referral.
This mapping covers specialist behavior, not proof of completed human action.
