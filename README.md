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

The cloud read fix is on main after PR #34. A full **292-test** regression passed; subsequent provider boundary and portal suites passed 9 and 28 tests respectively. Real accounts, the course model, recovery approval and restart reads were exercised. This does not constitute final unmodified submission-ZIP acceptance. See [workflow and limits](docs/stage2/LIVE_WORKFLOW.zh-CN.md); dated handoffs describe their original scope, including historical pre-merge status.

## First run from a ZIP: practical guide

This guide incorporates the October 29 ZIP installation and real portal rehearsal. See [demo scenarios and verification limits](docs/stage2/DEMO_SCENARIOS.zh-CN.md); final unmodified submission-ZIP acceptance remains pending.

1. Extract the ZIP first. The project root contains `README.md`, `pyproject.toml` and `scripts`. Do not run from an archive preview.
2. Open a terminal in that folder. On macOS, type `cd `, drag the extracted folder into Terminal and press Return; on Windows, open PowerShell in the folder. Keep quotes around paths containing spaces. A missing `scripts/setup_demo.py` usually means the wrong working directory.
3. Run installation below before editing `.env`. Finder can show hidden files with Command+Shift+Period. Use a plain-text editor, keep the exact name `.env`, and avoid `.env.txt` or Word documents.
4. A new computer does not require a new database. With the team's prepared Supabase project, configure access without replaying table creation. Without the original account password manifest, prepare separate rehearsal accounts below.
5. Keep the server terminal open. After `TripMate portals | http://127.0.0.1:8780`, open that address in a browser. The terminal remaining busy is normal; Ctrl+C stops the server. Closing the browser does not stop it.
6. Find credentials in the local `.demo-accounts…json` chosen during preparation: under `accounts`, select `free`, `paid`, `supplier` or `operator`, then use its `email` and `password`. Do not edit IDs, roles or passwords, commit the file or screenshot it. Ordinary registration does not create Supplier/Operator access.
7. Sign out before switching roles. Ordinary tabs in one browser share cookies; use separate browser profiles or different browsers for simultaneous roles. Opening `/admin` does not grant staff access.

### Separate rehearsal accounts without the original manifest

Complete installation and `.env` configuration first. Replace `yourname` with your own lowercase letters/digits to avoid an existing namespace. Keep the namespace and manifest unchanged when resuming the same accounts. The example travel dates suit the 5 November 2026 demo; later rehearsals need valid dates and a new scenario.

macOS / Linux:

```sh
.venv/bin/python -m tripmate.portal.demo --apply --confirm-project https://YOUR_PROJECT.supabase.co --namespace demo-yourname-20261105 --scenario rehearsal-one --manifest .demo-accounts-rehearsal.local.json --start-date 2026-11-07
```

Windows PowerShell:

```powershell
.venv\Scripts\python.exe -m tripmate.portal.demo --apply --confirm-project https://YOUR_PROJECT.supabase.co --namespace demo-yourname-20261105 --scenario rehearsal-one --manifest .demo-accounts-rehearsal.local.json --start-date 2026-11-07
```

The confirmation URL must exactly match `SUPABASE_URL`, not the dashboard URL. If a manifest is lost, use a separate namespace or contact the team administrator; do not delete cloud users, overwrite identities or repeatedly reset passwords. Retain a partially created manifest after failure so preparation can resume.

### Why are there no plans yet?

Preparation creates data without requester confirmation or Operator approval. Supplier inspects the quotes; Operator reviews ordinary inventory; Traveller opens and confirms a draft and starts processing. Generated plans still require review and controlled delivery before comparison/adoption. Starting the trip is a separate explicit Traveller action. Expired, zero-stock and restricted examples are not ordinary selectable inventory.

Wait for the current model operation rather than repeatedly clicking. A failure or human-assistance state is not success. If the port is occupied, add `--port 8781` and open the matching browser port; do not kill unfamiliar processes. After changing `.env`, stop your own server and restart it using the starter, then sign in again.

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

### If a cloud action appears to fail

Wait until processing finishes, then reopen the same request and inspect its history before repeating a write: a decision may have saved even if the following refresh failed. Use one active rehearsal tab per browser profile. The configured cloud already has the scoped-read migration; a different project must apply all missing migrations in filename order. See [cloud read fix](docs/stage2/SCOPED_CLOUD_READS.zh-CN.md). Do not clear records, disable approval or repeatedly click processing.
