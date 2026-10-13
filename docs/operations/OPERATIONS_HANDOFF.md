# Operations Agent implementation and handoff

Branch: `operations-agent`. Base: `1c83d8d` (`main`, B02/B03). Date: 13 October 2026, Australia/Sydney.
Owner: Jiaheng Guo. Design baseline: Stage 1 report OPS-02, OPS-03, OPS-AH-01, UC-05 and UC-07; AD-01, SD-01 and SM-01. Existing v1.0.0 public schemas are unchanged.

## What runs on this branch

Open the local application and choose **Open Operations desk**, or visit `/operations`.

```sh
.venv/bin/python -m tripmate.api.server --port 8765
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m tripmate --validate-examples docs/contracts/v1/examples
```

Use `.venv\Scripts\python.exe` on Windows. Follow the B02/B03 handoff for initial environment/dependency setup. The existing local-only host/origin checks, JSON body limit and `X-TripMate-Token` protection apply. No additional dependency is required.

1. Choose a **simulated** identity. B03 Free, Paid and unverified travellers, the fixture supplier and a fixture operator are available. This deliberate local role switcher is not production authentication.
2. Capture a request. Missing fields remain questions; independent intents can be confirmed as related cases through the API. An unverified identity can retain intake but cannot create or access protected cases.
3. Review and explicitly confirm the complete summary. Only then are strict shared `Case` records created. Confirmation does not route, release or adopt anything automatically.
4. Continue processing. Routine enquiries use approved service information. Membership uses deterministic rules. Unavailable specialist modules result in an open Human Assistance case with retained context.
5. Specialist proposals wait for response review. The operator can approve, request revision, reject or take over. Restricted responses require an exact-version, scoped human decision.
6. Select **Receive checked response**. Successful simulation saves a local inbox record and its delivery/closure traces in one transaction. The requester cannot see the formal response before that commit. Operator closure without delivery does not create a delivered message.

The optional automatic interpretation checkbox is enabled only when the campus adapter is installed and a local model key is configured. It sends only the redacted request message and a typed extraction schema. Model suggestions are unconfirmed. Invalid/low-confidence output leaves intake pending; deterministic rules retain authority. No successful live model call is claimed by this delivery; automated LLM checks use an explicit test substitute. Without the separate adapter, direct structured form intake remains usable.

## Functional features and Jira mapping

| Work item | Delivered Operations behaviour | Remaining team boundary |
|---|---|---|
| WN5620-7 / B06 | Source-tagged ExternalRequest, focused missing-field questions, typed extraction, explicit confirmation/split, role-based categories, routine enquiries and routing | Actual Supplier and Exception implementations are injected by their owners |
| WN5620-8 / B07 | Backend ownership checks; initial/post-generation/presentation/adoption entitlement decisions; Free two-trip and five-inclusive-day rules; active Paid exemption; current lifecycle counts | Replace fixture identity/membership evidence before any production deployment |
| WN5620-18 / B17 | Paid ad-free decision, labelled Free advertisement, backend route-map gate, interactive **schematic B03 route**, approved member-offer eligibility | Supplier owns discounted quotation/margin; UC-08 owns approved member rules. No discount quote is passed into PR #9 until its member-offer integration is ready |
| WN5620-22 | Case tracking, specialist clarification and full-summary re-confirmation, two human requests, withdrawal/operator closure, distinct assistance/approval states | Human Assistance is a handoff, not resolution of a complaint |
| WN5620-23 | Exact-version response review, immutable pending/decided approval history, restricted release gate, durable simulated delivery | Shared automatic Reviewer is optional and must be injected; explicit fixture operator review runs now |
| WN5620-24 | Confirmed TravelRequest/PlanningSpec, current-case loader, scoped access/entitlement ports, filtered plan/comparison reads, explicit adoption, preserved baseline and rechecked membership | PR #9 is not merged into this branch. `connect_planning` and the independent cross-branch acceptance script verify the integration boundary |
| WN5620-29 / OPS-O1 | Deterministic CTR, qualified-lead rate/conversion, simulated CAC and same-cohort retention; period, source IDs, missingness and zero-denominator handling | The operator supplies an explicitly simulated dataset; this does not claim a connected marketing feed. Campaign intake records retain source/consent and unassessed lead status |
| WN5620-30 / OPS-O2 | Evidence-linked experiment recommendation: hypothesis, control, one variable, segment, metric, duration, data requirement and stopping rule | Recommendation only. Supplier/UC-08 retain campaign design, approval, publication and spending responsibilities |

The two optional features are separate from the mandatory demo path. The route map represents the controlled B03 Sydney–Melbourne scenario; it is not a live geographic provider or arbitrary-route map. No booking, payment, refund, contract or advertisement is executed.

## Non-functional features

| Work item | Implementation and verification |
|---|---|
| WN5620-25 — Access/privacy | Local session binds the fixture identity server-side; request bodies cannot spoof requester IDs; ownership checks also cover direct API reads/adoption. Traveller-facing results omit raw specialist findings, supplier quote/cost/margin records and unreviewed LLM drafts. Credential/contact patterns are redacted from request text before storage/model use. This is data minimisation, not a general personal-data detector |
| WN5620-26 — Auditability | Strict `TraceEvent` records plus immutable per-event confirmation/state snapshots. Changes, snapshots and trace writes commit together. Operator-only snapshot endpoint reconstructs prior confirmed fields and membership decisions. A failed trace write rolls back delivery/closure. Operations exposes the shared TraceRepository methods; cross-agent B05 aggregation remains wrd's work |
| WN5620-27 — Reliability | Stable operation IDs with content fingerprints; replay protection, stale revision checks, single specialist invocation and preserved failure context. Dependency waits default to 30 seconds (configurable up to 60), with at most one outstanding dependency. Delivery retries preserve the same response; three failures escalate. Timeout stops waiting, **does not cancel** an already-running dependency: a late internal proposal cannot be released/adopted through the timed-out case |
| WN5620-28 — Interoperability/correctness | Shared schemas and matching case/traveller/correlation/action/version identities; typed constraints; Decimal/AUD wire amounts; inclusive calendar dates and timezone-aware timestamps. No LLM override of access, entitlement, prices or approvals. Independent cross-branch tests exercise the actual Planning implementation |

No numeric throughput, availability or latency SLA is inferred from the report. The bounded deadline is an implemented failure-control setting, not evidence of a performance SLA.

## Storage, restart and failure boundaries

The shared SQLite file contains Operations-owned `ops_records`, `ops_traces` and `ops_commands`. State, inbox delivery, approval records and audit history use these tables. B03 reset still touches only its own `fixture_*` tables and its separate Planning demo database. It does not reset Operations cases, decisions, inbox messages or membership fixtures.

Operations adds explicit fixture subscription evidence: the synthetic Paid subscription expires at `2026-10-30T00:00:00+11:00`. After expiry it is evaluated under Free rules. These records persist across restarts; choosing Paid in the role switcher does not invent a new subscription. Sessions expire after an hour and are intentionally lost on restart.

Closed/withdrawn cases cannot be re-confirmed or reviewed. Changed summaries invalidate prior response authority. Dispatch reservation is persisted before invoking a specialist without holding an Operations write lock. Interrupted or timed-out specialist work is not automatically replayed. The operator can take over or close with a reason; a new confirmed request is needed to retry unresolved specialist work.

Planning adoption and the Operations audit are two existing repository transactions, not a fabricated distributed transaction. If Planning commits but the Operations audit fails, the API does not claim completion. Operations reads Planning's canonical lifecycle for known plan IDs, so membership counts remain correct; retry reads the already-adopted exact version and completes the missing audit without adopting twice. All integrated customer adoption must enter through Operations; direct internal repository APIs are not authenticated endpoints.

## Connect PR #9 after it is merged

```python
from tripmate.operations import OperationsService, OperationsRepository
from tripmate.operations.integration import connect_planning
from tripmate.fixtures import FixtureRepository
from tripmate.planning.repository import PlanningRepository

fixtures = FixtureRepository(shared_database_path)
fixtures.ensure_seeded()
operations = OperationsService(OperationsRepository(shared_database_path), fixtures)
connect_planning(operations, approved_offer_adapter, shared_planning_reviewer,
                 PlanningRepository(shared_database_path))
```

`approved_offer_adapter` and `shared_planning_reviewer` must be supplied by their owners. The integration helper does not create passing Supplier/Reviewer fixtures. Its mode remains FIXTURE because the business evidence is simulated. For the web workbench, connect its existing `server.app.operations` instance rather than creating a second coordinator. Optional `planner=` accepts the Planning model engine; optional `clock=` supplies the shared timezone-aware clock. Configure provider deadlines within the coordinator deadline.

Verified against PR #9 head `a7d13e589d1b6398259394baf1719f8d2da6fd1a`:

- The actual `PlanningRuntime.load_context` calls with **caseId**, despite a mixed case-object example in the handoff. `OperationsService.load_context` accepts either the persisted current Case or its ID and rejects stale/spoofed payloads.
- The shared entitlement signature does not carry a plan ID. `CaseEntitlements` binds it to the confirmed case/baseline so revising/adopting an existing Free trip does not consume a third slot.
- Supplier bundles come from the existing `offer/price/product` port. Operations does not copy Planning source or pricing logic.
- `plan_view` requires Operations response delivery and returns the strict itinerary plus an explicit comparison allowlist. It never serialises the internal repository record or quote snapshots wholesale.
- `adopt_plan` requires a separately accepted exact version and expected selected baseline. Planning retains price/freshness/feasibility/review revalidation and its atomic selected-version transaction.

Use `build_agents(operations_service=operations)` to inject the shared Operations Agent boundary. `build_agents()` without dependencies preserves the existing explicit B01 stubs.

## Local HTTP surface

Operations writes use `X-TripMate-Token`, `X-Ops-Session`, JSON and a `requestKey`; session creation takes only an explicit fixture `identityId`. A session is not accepted in URLs. Extra body fields are rejected. The UI keeps request keys after a lost response so retrying does not create duplicate effects.

| Route suffix under `/api/operations/` | Method | Purpose |
|---|---|---|
| `status` | GET | Available fixture roles and dependency configuration |
| `session` | POST | Explicit local fixture-role session |
| `intake`, `update-intake`, `confirm` | POST | Capture, clarify/human request, explicitly confirm and split |
| `cases`, `case?caseId=...` | GET | Authorised filtered case views |
| `dispatch`, `clarify`, `case-action` | POST | Handoff, full-summary reconfirmation, human request/withdraw/operator close |
| `review`, `deliver` | POST | Operator review/scoped decision and simulated requester delivery |
| `traces?caseId=...` | GET | Role-filtered processing events |
| `history?caseId=...` | GET | Operator-only immutable decision snapshots |
| `premium` | POST | Current membership, map/ad-free or approved member-offer eligibility |
| `plan?versionId=...`, `adopt` | GET / POST | Reviewed delivered plan/comparison and explicit adoption (requires Planning injection) |
| `analysis` | POST | Operator-only simulated metrics/experiment recommendation with saved input provenance |

No direct specialist endpoint is exposed.

## Validation and peer review

See [TEST_RESULTS.md](TEST_RESULTS.md) for the completed checks and limitations. Do not mark Jira cards Done until another member reviews the branch and performs the required clean-start/group acceptance. No peer approval, live model success or four-agent completion is inferred from these tests.
