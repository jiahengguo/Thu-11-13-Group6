# Supplier B02/B03/B08 adaptation — 13 October 2026

Supplier now includes main `a1605f4` (Supabase portals and Operations).
The authenticated default entry, role checks, configuration, private cloud
repository and coordinator are preserved. No new public tables or Auth-account
migrations are introduced: new record kinds use existing backend-only RPCs.

## Run

```powershell
python -m pip install -e .
if (!(Test-Path .env)) { Copy-Item .env.example .env }
python -m tripmate.portal.server --port 8780
# Isolated local developer tools:
python -m tripmate.api.server --workbench --port 8765
```

Follow `docs/portal/PORTAL_HANDOFF.md` for Supabase setup and verified accounts.
Keep existing private configuration rather than replacing it with placeholders.
Merge Planning/B04 PR #9 and configure an explicitly reviewed Supplier policy:
`TRIPMATE_MARKUP_RATE`, `TRIPMATE_MINIMUM_MARGIN`, and
`TRIPMATE_PRICING_CONFIG_VERSION`. Tests' 10% / AUD 15 are examples, not activated
global defaults. Missing B04/policy records TOOL_UNAVAILABLE without inventing
prices; the portal still starts.

## B02 and B03

The default entry remains authenticated portals. The old workbench requires
`--workbench` and retains local model-smoke/catalog checks. Supabase environment
fields and portal static package resources are preserved.

The original deterministic B03 baseline/SQLite repository remains available.
SharedFixtureCatalog additionally stores it in private `demo_fixture_*` record
kinds. Operator -> Simulation catalog inspects/restores the baseline through
`GET /api/demo/fixtures` and `POST /api/demo/fixtures/reset`.
Existing session, Origin and CSRF checks apply. Reset atomically restores only
the active simulation manifest/catalog. It does not create, change or remove
Auth accounts, memberships, cases, assessed offers, decisions, traces or inboxes.
The 11 scenarios are expected outcomes, not completed specialist decisions.

## B08 integration

- Confirmed Operations intents contain structured `supplierOffer` source facts.
  Identity comes from the verified requester. Clients cannot supply approvals,
  state, version, pricing policy or internal evidence IDs.
- SharedSupplierRepository stores current pointers/history in private cloud
  records, with version/state-revision checks. Offer references are owner-scoped.
- Optional extraction cannot change independently confirmed source facts. The
  business prototype remains explicitly FIXTURE; no actual commitment is made.
- Valid priced proposals remain UNDER_REVIEW until an authenticated Operator
  records an evidence-backed SupplierOffer review. No automatic passing fixture
  reviewer is injected into the authenticated portal.
- Restricted terms need a separate persisted, version/review/scope-bound human
  decision. Cost, policy, validity and margin are rechecked before approval.
- Offer approval and Operations external-response authority remain separate.
  A Case response approval cannot approve a SupplierOffer.
- Idempotent action keys resume a domain decision saved before a Case-publication
  failure without repeating the decision.
- Source re-confirmation atomically invalidates old offer authority in the same
  coordinator transaction; redispatch creates a new material version. Historical
  snapshots remain intact. Withdrawn cases cannot supply selectable inventory.
- Supplier views omit company margins, raw reviews and approval history; other
  suppliers/Travellers cannot read or approve the assessment.
- Optional evidenced service metadata supplies ProductSpec. Planning gets only
  current approved/unexpired/authorised offer-price-product bundles.

Portal routes: `/api/supplier/assessment?caseId=...`, `/api/supplier/review`,
`/api/supplier/decision`. Operator writes carry case revision, materialVersion,
decision, reason and requestKey. The separate `/api/supplier-demo` remains a
workbench-only fixture demonstration. These adapters can also wrap the existing
SQLite OperationsRepository for local development tests.

## Verification and remaining evidence

Windows / Python 3.12.14: 115 discovered tests, 110 passed, 5 skipped because
B04/Planning is absent. In a temporary checkout with actual Planning `a7d13e5`,
**172/172 passed**. Shared contracts: **20/20**. Both scripts pass Node syntax.
Browser testing with synthetic identities/cloud substitute covered structured
submission, explicit confirmation, dispatch, visible source cost/base price/margin,
Operator offer review and APPROVED status; response release remains separately gated.
Additional tests cover ownership, self-approval rejection, real B04 arithmetic,
Planning lookup, source revision, withdrawal/revocation, missing policy, cloud
retry and isolated reset/rollback.

No live Supabase credentials or university-model call were exercised here.
Authentication/RLS infrastructure remains Jiaheng's implementation. Teammate
review and live-cloud reproduction remain Definition of Done evidence. B04 code
was used only in the temporary verification directory, not copied into this branch.
