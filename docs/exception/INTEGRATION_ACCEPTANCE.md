# Exception integration acceptance evidence

Date: 15 October 2026, Australia/Sydney. Base `main`: `1d74bb8` (merged PR #14).
Scope: **all 20 assigned To Do items**, including sprint work and backlog, not only backlog.
This record distinguishes implemented module scope from outstanding group acceptance.

## Verified results

- Full repository regression: **238 tests passed in 41.822 seconds**.
- Exception-focused regression: **38 tests passed in 6.382 seconds**.
- Existing shared contract examples are exercised by the full contract suite.
- Two consecutive fresh-data repetitions of eight controlled Exception scenarios: normal,
  approval waiting, conflict and missing evidence for both disruption and complaint.
  Machine-readable evidence: [integration-evidence.json](integration-evidence.json).
  Normal project recovery produced 52 linked trace events; normal delay complaint produced 39.
  Conflict remains `HUMAN_ASSISTANCE`; missing evidence remains `AWAITING_REQUESTER`.
- Real HTTP validation: reopened saved database, operator-only investigation access, hidden
  unreleased drafts, missing token rejection, scoped review, exact selection and re-review.
- Browser exercise on `/operations`: operator review, role switch, response receipt,
  **Confirm option 1**, and the resulting **UNDER REVIEW** state. The English options and
  decline control were visually inspected; there was no booking/payment.
- Git whitespace and JavaScript syntax checks passed. Tests made no live model/provider
  calls and performed no Supabase writes. Local socket tests require loopback permission.
- Python reported pre-existing `HTTPError` temporary-cleanup ResourceWarnings in legacy
  negative HTTP tests; all assertions passed. These warnings are not production health evidence.

Reproduce:

```sh
.venv/bin/python -m unittest discover -s tests
.venv/bin/python -m unittest discover -s tests -p 'test_exception*.py'
```

## All assigned To Do items: code and remaining acceptance

Card links use the project's [Jira board](https://elec5619-5-group-1.atlassian.net/jira/software/projects/WN5620/boards/34).
No card is claimed Done solely because code or automated tests exist; the existing cards'
Definition of Done also requires another member's review and shared-project integration.

| Jira | Requirement / work | Evidence in this branch | Remaining acceptance |
| --- | --- | --- | --- |
| [WN5620-6](https://elec5619-5-group-1.atlassian.net/browse/WN5620-6) | B05 shared traces | Operations merges linked persisted traces; atomic Exception snapshot receipt, operator history and privacy tests | Peer review and broader shared-project acceptance |
| [WN5620-11](https://elec5619-5-group-1.atlassian.net/browse/WN5620-11) | B10 shared review/approvals | Shared validator registry and Exception callback; existing Operations review workspace; separate proposal/response decisions | Cross-domain owner composition and Campaign validators; campaign module absent in inspected base; peer review |
| [WN5620-13](https://elec5619-5-group-1.atlassian.net/browse/WN5620-13) | EXC-01 / UC-03 recovery | Project Supplier lookup and Planning recovery; preserved requirements, comparison, review and selection | Team integration review; unsupported Planning scope stays manual |
| [WN5620-16](https://elec5619-5-group-1.atlassian.net/browse/WN5620-16) | EXC-02 / UC-04 complaints | Existing delay policy investigation plus specialist findings adapter; unsupported policy -> human | Team review; wider policies require business-owner inputs |
| [WN5620-20](https://elec5619-5-group-1.atlassian.net/browse/WN5620-20) | B19 release acceptance | Full current suite and Exception success/failure/approval scenarios repeated twice from fresh data | Supplier/Campaign contributor release evidence and whole-release review remain; not a complete three-set release sign-off |
| [WN5620-39](https://elec5619-5-group-1.atlassian.net/browse/WN5620-39) | Simulated EXC-01 | Original merged prototype retained; `test_exception.py` and integration regression | Review acceptance record |
| [WN5620-40](https://elec5619-5-group-1.atlassian.net/browse/WN5620-40) | Simulated EXC-02 | Delay facts/policy preserved; normal and negative scenarios repeated | Review acceptance record |
| [WN5620-41](https://elec5619-5-group-1.atlassian.net/browse/WN5620-41) | Persistence/traceability | Append-only specialist runs and imported Operations records; restart and rollback tests | Peer review |
| [WN5620-42](https://elec5619-5-group-1.atlassian.net/browse/WN5620-42) | Oversight boundaries | Risk referrals, exact-version approvals, unauthorised/stale release rejected | Peer review |
| [WN5620-43](https://elec5619-5-group-1.atlassian.net/browse/WN5620-43) | English demo/testing | Existing two-button demo plus English Operations choices; run guide and new HTTP tests | Peer demonstration review |
| [WN5620-44](https://elec5619-5-group-1.atlassian.net/browse/WN5620-44) | EXC-01 specialist integration | `integration.py`, `project_ports.py`, normal integration CLI; actual B03 lookup and Planning engine | Peer review; live supplier authentication remains out of scope |
| [WN5620-45](https://elec5619-5-group-1.atlassian.net/browse/WN5620-45) | Existing Planning preferences/constraints | `test_exception_project_ports.py`: preservation, accessibility rejection, unconfirmed changes blocked | Peer review; no new unsupported constraint rules |
| [WN5620-46](https://elec5619-5-group-1.atlassian.net/browse/WN5620-46) | Other complaint findings | `ProjectComplaintFindings`; source collection and no-policy human-referral test | Peer review; trusted context/policy owner wiring in deployed composition |
| [WN5620-47](https://elec5619-5-group-1.atlassian.net/browse/WN5620-47) | Same-case clarification | Missing evidence -> Operations questions -> confirmed correction -> saved successor, original preserved | Trusted evidence-source injection required; no arbitrary browser evidence writer |
| [WN5620-48](https://elec5619-5-group-1.atlassian.net/browse/WN5620-48) | Proposal revision/re-review | Failed review correction test; `previousSubject`, `previousReviewId`, version increments, old decision denied | Peer review; manual confirmed resumption, no invented automatic retry count |
| [WN5620-49](https://elec5619-5-group-1.atlassian.net/browse/WN5620-49) | Agreed SM-03 lifecycle | Selection/decline, proposal decisions, response delivery, operator unresolved closure, privacy tests | Reminders explicitly deferred; external execution and proof of recovered travel remain manual |
| [WN5620-50](https://elec5619-5-group-1.atlassian.net/browse/WN5620-50) | Shared case evidence | Full immutable investigation imported, source/check/review links, actor/scope decisions, reopen/rollback tests | Peer review |
| [WN5620-51](https://elec5619-5-group-1.atlassian.net/browse/WN5620-51) | Shared review/policy gates | Common `ReviewService`, Exception validators, recomputation, missing policy/version/stale evidence tests | Cross-domain B10 owner composition is separate; peer review |
| [WN5620-52](https://elec5619-5-group-1.atlassian.net/browse/WN5620-52) | Exception approval-pending compatibility | `AWAITING_HUMAN_APPROVAL` recognised; approve/revise/reject/takeover; separate immutable proposal/response records | Peer review |
| [WN5620-53](https://elec5619-5-group-1.atlassian.net/browse/WN5620-53) | Reliability/retry consistency | Repeated command, failed import, restart, stale approval/quotes, confirmed resume, late result after withdrawal | Peer review; existing Operations timeout/manual recovery contract retained |

Functional mappings come from EXC-01, EXC-02, EXC-AH-01/02, UC-03/04 and the agreed
SM-03 subset. NFR labels classify the report's traceability, review, oversight and failure
requirements; they do not invent numbered report NFRs. EXC-O1 and automatic reminders are
deferred. No financial entitlement, unsupported policy, actual recovery or group review is inferred.

## Storage and release interpretation

`SUCCESS` is a saved internal recommendation. `APPROVAL_PENDING` is a saved request for a
scoped human decision. Neither authorises a booking/payment nor directly contacts a traveller.
The local inbox represents simulated Operations delivery. Recovery remains open after delivery;
explicit operator closure is labelled `CLOSED_UNRESOLVED`. Complaint closure means the checked
recommendation was delivered, not that a refund/compensation or liability decision was executed.
Each persisted assessment uses its declared synthetic clock; record time is stored separately.
