# Planning and recovery lifecycle implementation

Planning assessment is a separate durable aggregate (`planning_assessment`),
with version references and append-only `planning_assessment_event` history.
It does not change immutable ItineraryVersion records or trip status.

| State | Trigger / implementation |
| --- | --- |
| DRAFT | Confirm/reconfirm a request |
| VALIDATING | Persisted Operations dispatch start |
| FEASIBLE | Durable phase event after deterministic candidate validation, before domain review |
| UNDER_REVIEW | Durable domain-review start, followed by saved candidates awaiting Operations review |
| REVISION_REQUIRED | Failed domain review, dependency repair, or operator request revision |
| INFEASIBLE | No candidate satisfies constraints |
| AWAITING_HUMAN_REVIEW | Pending human approval or takeover |
| REVIEWED | Operator approves the exact current response |
| REJECTED | Operator rejects, withdraws, or closes without delivery |
| HANDED_OFF | Reviewed response persisted in requester inbox |

Request revision requires reconfirmation and regeneration before approval;
old candidates remain immutable. Failed domain-review candidates are stored
privately and never returned as successful subjects. Failed persistence releases
no successful result. Existing request keys and case revisions govern retries.
Feasibility and domain review are synchronous, with durable phase events bound
to the current dispatch revision. They are not external waiting states. Candidate
records also preserve assessment history. A late invocation cannot overwrite a
reconfirmed, withdrawn or reassigned case.

`POST /api/operations/planning-lifecycle` accepts `requestKey`, `caseId`,
`revision`, `action`, `reason`. Operator-only `RETRY` permits unchanged-input
retry only for dependency/timeout/persistence failures. `REOPEN` requests
traveller reconfirmation before regeneration. Rejected or infeasible plans cannot
use a technical retry to bypass reconfirmation. Old run IDs and immutable versions
remain available. Editing response text cannot convert a failed run to success.

Restricted quotes carry the actual Approval returned by trusted Supplier lookup.
Planning checks exact source, offer version, review, scope and timestamps;
fresh Supplier lookup rechecks storage and operator authorization at validation
operator approval, delivery and adoption. Each release also repeats deterministic
validation, domain review and (where applicable) daily-factor checks. Restriction
flags are retained. Failed-review candidates cannot be adopted directly.

Recovery retains investigation, clarification, proposal approval, selection and
delivery. Operators can configure deadline, reminder interval and maximum count
while waiting for a traveller. No business deadline defaults are invented.
`CHECK_WAIT` is an explicit operator-triggered due check, not a background worker.
It saves bounded local reminder records visible to the traveller; no email/SMS is sent. Expiry enters
NO_RESPONSE / HUMAN_ASSISTANCE. Expired selections are blocked even before a due
check. Reconfirmation clears old waiting/completion metadata.

After the selected recommendation is reviewed and delivered, an operator can
record its exact run/option, evidence reference and reason as simulated
completion. Current itinerary/evidence, quote validity, proposal authorization,
response review, response approval and the exact delivered response version are
checked. Completion, case closure, trace and idempotency receipt commit atomically;
a failed save leaves the case incomplete and the same request can be retried. Only then does
this path reach RESOLVED_SIMULATED / CLOSED. Ordinary unresolved closure remains
CLOSED_UNRESOLVED. No booking, payment or refund is executed.

Portal controls expose waiting policy, due checks and completion evidence.
Testing uses authenticated isolated cloud fixtures; live browser, actual peer
review and any team approval of model scope remain separate acceptance steps.

## Prototype API and verification boundaries

`POST /api/operations/recovery-lifecycle` accepts `requestKey`, `caseId`,
`revision`, `action`, `data`. Operator-only actions:

- `CONFIGURE_WAIT`: explicit timezone-aware future `deadline`, integer
  `reminderMinutes` (1–10080), `maxReminders` (0–10). These bounds limit prototype
  processing, not an assumed business service-level agreement. Reconfiguration
  gets a new policy ID so existing reminders are not overwritten.
- `CHECK_WAIT`: empty data; no event before due time, bounded reminders thereafter,
  human follow-up at deadline. Each future check needs a fresh request key;
  replaying one key never sends another reminder. A scheduler can invoke this
  same command later; no background scheduler or external notification is claimed.
- `COMPLETE`: exact `runId`, selected `optionId`, nonempty `evidenceReference`,
  `reason`, and `confirmed: true`. Records only an operator-attested simulated
  outcome; the evidence reference is retained, not fetched or verified by a
  real booking provider.

All routes use existing authenticated sessions, CSRF protection, role checks,
case revisions and idempotency. No new credentials or database migrations are
required: state uses existing generic Operations records. A real booking or
notification adapter and team peer acceptance remain outside these local
simulation transitions.

Verification commands: `python -m unittest discover -s tests -q`,
`node --check src/tripmate/portal/static/portal.js`, `npm test` and
`npm run build` in `web`. Authenticated HTTP regressions cover restricted
supplier approval/revocation, every Planning assessment phase, immutable history,
reconfirmation, retry, rejection, expiry before due-check, bounded reminders,
completion access/version checks, rollback, replay and persistence across restart.

### Local evidence — 1 November 2026

- Full backend run: 349 cases; 347 passed and two new assertions expected HTTP
  409 where the existing API returns 422 for stale evidence. After correcting
  those assertions, both affected authenticated suites passed (24 cases).
- Planning unit suite: 45 passed, including retained failed-review candidates
  that cannot be adopted. Final deadline-input and rejection/reconfirmation
  checks: 2 passed after the final boundary edits.
- Frontend: 15 tests passed; production build succeeded and generated queue
  bundles match the checked-in content. Native portal JavaScript syntax check,
  Python compilation and `git diff --check` passed.
- These are isolated fixture/HTTP checks, not a live-provider browser run or
  peer acceptance sign-off. Jira status is not changed by this implementation.
