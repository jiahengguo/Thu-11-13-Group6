# TripMate AI

[简体中文](README.zh-CN.md) · [Documentation index](docs/index.md)

TripMate is a travel-service prototype with authenticated Traveller, Supplier and Operator portals. Operations coordinates three specialist agents: Supplier validates quotations, Planning proposes and checks itineraries, and Exception investigates disruptions and prepares recovery recommendations.

Supabase provides real authentication and private persistent records. The course `campus-qwen` model supports extraction and itinerary proposals. Deterministic rules enforce prices, availability, membership, constraints and approval boundaries. Travel inventory, cancellations and transactions are simulated; the prototype does not book, charge, refund or rebook travel.

## Current scope

- Supplier quotations, explicit Operator review and deterministic AUD pricing.
- Confirmed travel requests, model-assisted plan comparison, explicit adoption and immutable revisions.
- Traveller-confirmed trip activation; adopting a revision preserves Active status and the original start time.
- Cancellation evidence recorded by an Operator, Supplier/Planning recovery recommendations, separate proposal/response approvals and controlled delivery.
- Role/ownership checks, private case histories, idempotent commands and durable audit trails.

PRs through #26 are integrated. The last implementation regression passed **283 tests**; real cloud accounts and the course model were exercised on the supported planning/recovery flow. This does not constitute fresh-machine or final ZIP acceptance. See [workflow and limits](docs/stage2/LIVE_WORKFLOW.zh-CN.md); dated handoffs describe their original scope, including historical pre-merge status.

## Quick start

Run commands from the source root. Requirements: **Python 3.9+**, Internet access for installation/Supabase, and campus network or USYD VPN access to the course model. No Docker setup is required.

### 1. Install

macOS / Linux:

```sh
python3 scripts/setup_demo.py
```

Windows PowerShell:

```powershell
py -3 scripts/setup_demo.py
```

This creates `.venv`, installs the package and creates `.env` from `.env.example` only if it is missing. Existing configuration and data are preserved. Installation does not deploy database migrations or create accounts.

### 2. Configure one file

Edit **the root `.env` only** for the authenticated demo. All agents use the same server configuration; do not edit individual modules or put keys in browser code.

```dotenv
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_PUBLISHABLE_KEY=YOUR_PROJECT_PUBLISHABLE_KEY
SUPABASE_SECRET_KEY=YOUR_PROJECT_SERVER_SECRET
TRIPMATE_LLM_PROVIDER=elec5620
TRIPMATE_LLM_MODEL=campus-qwen
ELEC5620_API_KEY=YOUR_COURSE_KEY
ELEC5620_BASE_URL=http://10.167.60.148:8000/v1
ELEC5620_MODEL=campus-qwen
```

The three Supabase values must belong to the same project. Leave other template settings unchanged for the supported local demo. The starter explicitly enables simulated pricing: 10% markup, AUD 15 minimum margin, policy `demo-2026-10-24`. Without that flag, a direct server launch needs an explicitly configured pricing policy.

For a **fresh Supabase project**, an administrator must apply the SQL files in `supabase/migrations/` in filename order. An existing prepared project should not replay the initial table-creation migration. See [cloud setup](docs/portal/PORTAL_HANDOFF.md) and [demo provisioning](docs/stage2/DEMO_ACCOUNTS.zh-CN.md). Supplying keys alone does not create the database schema. Tutor credential delivery is still to be agreed.

### 3. Prepare demo accounts and inventory, if needed

Preview without cloud writes:

```sh
.venv/bin/python -m tripmate.portal.demo
```

Explicitly prepare a named simulated scenario in the configured project:

```sh
.venv/bin/python -m tripmate.portal.demo --apply --confirm-project https://YOUR_PROJECT.supabase.co --start-date 2026-11-07
```

Use `.venv\Scripts\python.exe` instead on Windows. Choose future travel dates for your rehearsal. The four account types are Free/Paid Traveller, Supplier and Operator. Random passwords are saved only in the ignored `.demo-accounts.local.json`. New machines without the original manifest must use an agreed credential handoff or a new `--namespace` and separate manifest; never overwrite existing identities. A new `--scenario` creates a separate rehearsal while retaining history.

Provisioning does not approve quotations, confirm traveller requests or activate trips. Expired, zero-stock and restricted examples intentionally remain blocked/pending. Normal planning uses the four ordinary quotations after Operator review.

### 4. Check and start

macOS / Linux:

```sh
.venv/bin/python scripts/start_demo.py
```

Windows:

```powershell
.venv\Scripts\python.exe scripts/start_demo.py
```

Open **http://127.0.0.1:8780**. The starter checks cloud storage, explicit demo pricing and a real model smoke call before starting the authenticated portal with model planning enabled. To change the port, add `--port 8781`.

| Portal | Route | Purpose |
| --- | --- | --- |
| Traveller | `/app` | Confirm requirements, compare/adopt/revise plans, start a trip and select reviewed recovery options |
| Supplier | `/supplier` | Submit quotations and inspect assessments |
| Operator | `/admin` | Review quotations, record simulated cancellation evidence, approve and release responses, inspect traces |

Use accounts with the appropriate backend role; ordinary registration creates a Traveller, not staff access. Follow the [walkthrough](docs/stage2/LIVE_WORKFLOW.zh-CN.md) for the review/delivery sequence.

## Checks and troubleshooting

```sh
.venv/bin/python -m tripmate.portal.doctor --demo-pricing --check-cloud --check-model
.venv/bin/python -m unittest discover -s tests -v
```

- **Cloud check fails:** verify matching project keys, project availability and applied migrations. The server secret stays server-side.
- **Model check fails:** connect campus network/VPN and check the course key. A skipped probe or fixture run is not a successful live-model check.
- **Accounts cannot be prepared:** verify the demo-profile migration and the manifest's project/namespace. Do not clear the shared database to retry.
- **Plans unavailable:** normal offers need current stock, validity and Operator review; incomplete or pending results are intentionally hidden.
- **After restart:** sign in again. Sessions are process-local; cloud business records persist.

## Repository and remaining work

| Path | Contents |
| --- | --- |
| `src/tripmate/` | Portal, Operations, Supplier, Planning, Exception, shared services/contracts and adapters |
| `scripts/` | Setup/start and verification entry points |
| `supabase/migrations/` | Ordered database migrations |
| `tests/` | Automated regression tests, including explicitly isolated transport doubles |
| `docs/` | [Indexed implementation guides and historical handoffs](docs/index.md) |

Trusted complaint-policy integration, restricted supplier offers in Planning, remaining state-machine/reminder behavior, Campaign and full membership benefits remain incomplete. Production pagination/scaling is also outside the current single-process demo. The private snapshot has a bounded 32 MB limit.

New-machine acceptance, team release rehearsals, final documentation/contribution statements and final ZIP extraction/deployment checks remain pending. Never include `.env`, `.demo-accounts*.json`, virtual environments or local databases in the submitted source package. The retained [Stage 1 report](docs/TripMate_AI_stage1_report.pdf) is the design reference; separate modelling drafts and UML files have been removed.
