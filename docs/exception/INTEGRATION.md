# Customer Exception: Operations integration

Branch: `codex/customer-exception-agent`; base: `main` at `1d74bb8`.
Scope agreed by the module owner on 15 October 2026. The report remains unchanged.
The implementation uses Python, the existing shared v1 contracts and local SQLite.
No additional dependency, model key, live TripMate connection or Supabase write is required.

## What changed

- Operations dispatches its current confirmed case to the registered Exception bridge;
  saved evidence must belong to that case, traveller and affected plan.
- Recovery can use `ProjectSupplier` with the project's `find_selectable(criteria, at)`
  port (B03 approved offers or SupplierGateway) and `ProjectPlanning` with the installed
  Planning engine. Existing typed preferences/constraints and validation are retained;
  unchanged hotel/activity resources are preserved. Unsupported inputs require human help.
- `PlanningEngine.recover` re-evaluates resources while preserving the confirmed request
  and constraint meanings. It does not weaken ordinary preference-revision confirmation.
- Other complaint categories can collect `ProjectComplaintFindings` from the installed
  Planning repository and Supplier lookup. Without an agreed category policy they return
  facts and an explicit human referral. Delay policies remain explicitly supplied fixtures.
- Missing evidence/review corrections return questions through Operations. After confirmed
  clarification and trusted evidence replacement, the same case can run again. Proposal
  versions link to the previous subject and review; old approvals cannot authorise successors.
- The shared `ReviewService` implementation uses common evidence/version gates and an
  explicit domain-validator registry. Exception validators recompute costs, delay and
  supplied policies, including Planning checks. Unregistered domains fail for revision.
- Exception proposal decisions and Operations external-response decisions have distinct
  scopes and saved records. Approve, Request revision, Reject and Take over retain the
  operator, timestamp, reason and exact version. Approval never executes a transaction.
- Operations imports the complete Exception snapshot and traces atomically with its case
  receipt. A failed import rolls back; a late result cannot overwrite withdrawal. Existing
  Operations idempotency and manual resumption rules apply. No automatic retry policy is added.
- Reviewed recovery options reach the traveller only through the Operations local inbox.
  Exact selection or declining all is recorded. A selection returns for response review;
  after delivery, recovery remains open. An operator can explicitly close unresolved with
  a recorded reason. No changed booking or successful real-world recovery is asserted.

## Run both examples

From the repository root, after the normal editable installation:

```sh
.venv/bin/python -m tripmate.exception_handling.integration_demo --case disruption --database data/exception-recovery.sqlite3
.venv/bin/python -m tripmate.exception_handling.integration_demo --case complaint --database data/exception-complaint.sqlite3
```

Each command creates a synthetic confirmed Operations case and stops at review. Recovery
uses the actual B03 approved-inventory lookup and Planning engine; the complaint uses the
original explicit service/policy fixtures. Each has its own database and declared fixture
clock. Reusing a database with an incompatible fixture clock/adapter configuration is refused.
The fixture clock is intentionally fixed so the demonstration remains reproducible.

For a complete **scripted simulation** of operator decisions and traveller selection,
add `--scripted-decisions` to either command. Its output clearly labels scripted decisions;
without that flag no human decision is fabricated. Available scenarios are `normal`,
`approval`, `conflict` and `missing-evidence`. Approval/conflict/missing examples use the
original explicit Supplier/Planning simulation ports, as indicated in the output.

## Demonstrate manually in the existing English web page

Seed one of the databases using the command above **without** scripted decisions, then:

```sh
TRIPMATE_EXECUTION_MODE=FIXTURE TRIPMATE_DATABASE_PATH=data/exception-recovery.sqlite3 .venv/bin/python -m tripmate.api.server --workbench --exception-fixture --port 8770
```

Open **http://127.0.0.1:8770/operations**.

1. Select `operator:fixture`, then **Use this identity**. Open the disruption case.
2. Inspect **Exception investigation · operator only** and **Processing history**.
3. Enter the evidence/reason and **Record reviewed decision**. In the normal case this
   approves the current response. In an approval scenario, first approve the Exception
   proposal and then separately review/approve its response.
4. Switch to `traveller:paid`, reopen the case, and **Receive checked response**.
5. **Confirm option 1**, or **Decline all options and ask for a human**. A selection returns
   to review. Switch to the operator and approve the exact selected response, then use
   the traveller role to receive it. Only the operator can close with a recorded reason.
6. For complaints, stop the server and reopen `data/exception-complaint.sqlite3` with the
   same flag. Inspect the saved delay facts and policy, review, then receive the response.

These identities are local simulations, not production authentication. Do not combine
`--exception-fixture` with `--planning-fixture`: they have separate explicit fixture clocks.
The ordinary two-button standalone Exception panel remains available at `/#exception-panel`.
The new bridge is opt-in; the default cloud portal and other agents are not silently rewired.

## Adapter contracts

`connect_exception(operations, contexts, repository, supplier, planning, reviewer=None,
complaint_findings=None)` registers `operations.specialists['exception']`.

| Input or result | Structure |
| --- | --- |
| Confirmed case | Existing shared `Case`; must equal the persisted Operations case in progress |
| Trusted context | Existing `ExceptionContext` evidence, affected itinerary, costs, risk/approval flags, constraints, policies and assessment time |
| Planning extension | Optional `planningContext = {request: TravelRequest, spec: existing Planning spec, baseline: saved Planning record}` |
| Complaint extension | Optional `complaintCategory`: `DELAY`, `ITINERARY` or `SUPPLIER_TERMS` |
| Internal handoff | Existing `AgentResult`, `handoffTo=operations`, immutable snapshot, proposal/review, exact-version approvals and traces |
| Selection command | `{requestKey, caseId, revision, runId, optionId, confirmed:true}`; `optionId:null` explicitly declines all |
| Human decision | Existing Operations review command; proposal approval is distinct from response approval |

The trusted `contexts.load(caseId)` port is intentionally injected. Only explicit synthetic
contexts are persisted by the demo; no public endpoint accepts arbitrary evidence updates.
For real integration, Operations' evidence owner supplies a replacement context after
confirmed clarification. The automated resumption tests exercise this contract directly.
Do not treat edited request text as authenticated supplier evidence.

Saved local records: `exception_runs` plus Operations-owned `exception_run`,
`exception_approval`, versioned response approvals, inbox and case history. Earlier snapshots
remain intact. The operator-only `GET /api/operations/exception?caseId=...` returns investigation
details; travellers receive only the reviewed delivered response/options and redacted history.
POST selection uses the existing local token/session, authorisation, revision and idempotency gates.
Before approval/delivery/selection, current project quotes, validity and Planning checks are
rechecked. Changed resources/terms require investigation of a successor proposal.

## Explicit remaining boundaries

- Automatic reminders, configured waiting deadlines and EXC-O1 are deferred by the owner.
- No live provider authentication, cloud composition, direct traveller contact, booking,
  payment, refund, compensation, legal finding or inferred financial entitlement is added.
- Existing Planning capabilities define supported scope; this adapter does not supply missing
  route topology, daily-factor policies or unsupported business constraints.
- The shared registry supplies Exception validators. Supplier/Planning retain their existing
  review flows; cross-domain B10 acceptance, especially Campaign, requires owner integration.
- Recovery closure records an unresolved/manual outcome; external execution and proof of a
  genuinely recovered trip require the responsible manual workflow and are not simulated as fact.
- Team review/merge and whole-release acceptance remain outstanding. See the per-card matrix.
