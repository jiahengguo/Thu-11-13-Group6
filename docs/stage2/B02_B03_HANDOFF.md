# B02 + B03: Local workbench and deterministic fixture handoff

**Date:** 2026-10-13 (Australia/Sydney)  
**Owner:** Jason (Supplier Partnership)  
**Scope:** WN5620-3/B02 and WN5620-4/B03 only. Do not claim that B08 Supplier, B06 Operations, B10 Reviewer, or four-agent end-to-end flows are implemented.

## Start the application (Windows PowerShell)

The `supplier-partnership` delivery folder contains changed files only. Apply
them at matching paths in a branch based on the team repository's `main`; it
relies on the shared contracts and framework already in that repository.
Keep an existing teammate dependency declaration when merging `pyproject.toml`
(for example, Planning's `tzdata` dependency). Do not replace an integrated
repository with this partial folder.

From the **repository root** (the folder containing `pyproject.toml`):

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m tripmate.api.server --port 8765
```

Then open `http://127.0.0.1:8765` in a browser. The web app is intentionally **bound to localhost** and designed for a classroom prototype, not deployment on a public server. On the default `.env` settings, business workflows are **FIXTURE**. You can inspect startup/persistence checks, view B03 data and safely reset simulation fixtures. The optional Planning fixture demo becomes available after Moore’s separate branch is merged.

To run tests in another PowerShell window:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m tripmate --validate-examples docs/contracts/v1/examples
```

For Linux/macOS, replace `py -3` with `python3` and use `.venv/bin/python` instead of `.venv\Scripts\python.exe`. Initial dependency installation needs network access. No passwords/API keys are provided in this repository.

## Local API (B02)

| Route | Method | What it does |
|---|---|---|
| `/` | GET | Static, simulated workbench UI |
| `/api/status` | GET | Local backend, SQLite, fixture mode and LLM-key configured indicator |
| `/api/checks` | GET | Persistent records of LLM smoke and isolated Planning demonstration |
| `/api/planning-demo` | POST | Optional Moore Planning: returns `PLANNING_NOT_INSTALLED` until his branch is merged, then runs using a **separate** `*.planning-demo.sqlite3` database |
| `/api/model-smoke` | POST | Attempt synthetic model extraction only when configured and the separate campus adapter is installed; otherwise persist a `BLOCKED` record with reason |
| `/api/fixtures` | GET | Fixture counts, expected scenarios, FK integrity (expectations, not executed workflow outcomes) |
| `/api/fixtures/reset` | POST | Restore only `fixture_*` tables in the shared DB; clear separately named Planning **demo-only** database tables when present |

The POST routes require `Content-Type: application/json` and `X-TripMate-Token` returned by `/api/status`, and are limited to local browser requests. They are **not production authentication**. `STUB` mode disables the B03 catalog/reset and Planning demonstration; it does not magically enable real business operations.

The campus model smoke check accepts **no user-supplied content**, uses only a synthetic example and does not persist credentials or raw model outputs. If `ELEC5620_API_KEY` is absent, the persisted outcome is `BLOCKED/MODEL_NOT_CONFIGURED`. A real model connection must be verified manually from the university-accessible network/VPN using a personal key in local `.env` (ignored by git). Neither fixture runs nor a mock test count as a successful live LLM call.

## B03 synthetic dataset

Module: `src/tripmate/fixtures/b03.py` (stable, versioned fixture schema). It is stored in the **same** `TRIPMATE_DATABASE_PATH` SQLite database as the shared workbench, under separate `fixture_*` tables. The B03-owned `sample_quotes.json` holds six deterministic, synthetic, Planning-compatible quote examples prepared from the agreed demo scenario; it does not import Moore’s source code or run his pricing engine. It **does not replace** his independent Planning runtime or fake human approvals in that runtime.

Data at fixed time `2026-10-12T10:00:00+11:00`, with fixture-only source references:

- 2 fake suppliers, 6 products, 6 approved *fixture-only* offers, 6 verified fixture price examples.
- 6 negative/pending source inputs: expired offer, zero stock, missing supplier cost, unsupported USD input, missing cancellation terms, restricted commitment awaiting approval. These are intentionally **unvalidated raw candidate inputs**, not approved `SupplierOffer` business outputs.
- 3 simulated travellers (Free, Paid, unverified); 3 request cases; 3 itineraries (one active Paid, two Free Planned/Active); 1 affected transport cancellation, 1 complaint and 1 simulated **pending** human-approval placeholder.
- 11 expected-outcome scenarios with stable `scenarioId` and `entityIds`: paid eligible path, six invalid/pending offers, Free trip-count and six-day limits, cancellation with alternative and complaint.

All data is explicitly marked simulated; **no real provider feeds, bookings, payments, refund, advertising or approval records** are created.

### Python access for teammate integration

```python
from tripmate.fixtures import FixtureRepository

fixtures = FixtureRepository("data/tripmate.sqlite3")
fixtures.ensure_seeded()  # no-op if current baseline already exists
offers = fixtures.list_entities("OFFER")
invalid_source_inputs = fixtures.list_entities("OFFER_INPUT")
single = fixtures.get_entity("candidate:zero-stock")
scenarios = fixtures.summary()["scenarios"]
# Explicit local operator action only, and only in FIXTURE mode through HTTP:
# fixtures.reset()
```

**Boundary:** `OFFER` means an explicitly approved *simulated fixture*, not a B08-reviewed actual SupplierOffer. `OFFER_INPUT` deliberately contains malformed raw candidates for B08 to reject. The expected outcomes are **test expectations**. They do not establish that B07 entitlement, B08 margin, B10 human approval or B12 recovery functions have run.

### Reset semantics

`POST /api/fixtures/reset` is an explicit local operator action. It transactionally restores **only** B03-owned `fixture_*` tables in the shared `TRIPMATE_DATABASE_PATH`. It never deletes `planning_*`, `approvals`, `trace_events`, `cases` or other tables from that shared database. If Moore’s isolated Planning demonstration has been run, its records live in a **separately named** sibling `*.planning-demo.sqlite3` database, and the reset also clears only the five known `planning_*` tables there. A normal application restart preserves both databases; initial seeding does not erase previous runs.

All B03 entity IDs, source references and scenario associations are deterministic; SQLite foreign keys enforce relationship integrity. A failed reseed rolls back atomically, preserving the last complete baseline. Reset twice should produce exactly the same B03 JSON snapshot, restore the **pending** approval fixture and remove any prior Planning demo versions/acceptances. Shared non-fixture records are intentionally preserved. This local-only route is unavailable outside `FIXTURE` mode. It is not an authenticated production reset service.

## What is complete vs. still dependent on the team

| Jira acceptance criterion | Evidence | Result |
|---|---|---|
| B02-AC1 clean checkout starts application | `pyproject.toml`, local start instructions, `test_b02_b03.py` HTTP startup | Implementation + automated local check; independent teammate reproduction pending |
| B02-AC2 frontend/backend/SQLite reachable, no secrets in template | HTTP GET `/`, GET `/api/status`, SQLite check, `.env.example` | Automated tests pass |
| B02-AC3 real LLM smoke succeeds **or blocker recorded**, distinct fixture | `POST /api/model-smoke`, `LLM_SMOKE` persisted with `MODEL_NOT_CONFIGURED` if no personal key | Blocker handling tested; live campus network/key check pending |
| B03-AC1 valid/expired/missing/zero stock/membership/cancel/complaint/approval | `baseline()`, `/api/fixtures`, 11 expected scenarios | Fixture data created; execution of downstream UC flows pending |
| B03-AC2 references valid after reset | FK relations, `PRAGMA foreign_key_check`, negative constraint test | Automated tests pass |
| B03-AC3 two resets identical, earlier simulated approvals/revisions cleared | Snapshot equality, mutation/rollback and separate Planning demo wipe tests | B03 fixture approval reverts to pending; optional demo revisions cleared only in separate DB; shared team records intentionally preserved |

Run `python -m unittest discover -s tests -v` before making Jira completion claims. Jira's Definition of Done additionally requires a **real commit/PR, other-member review, evidence attachment, and clean-start reproduction by a teammate**. Do not mark the cards Done until those happen. Git history was not available in the ZIP source snapshot.

## Branch ownership and integration boundary

This change set is based on the team `main` baseline. Do not copy Moore’s `src/tripmate/planning/`, `src/tripmate/adapters/campus.py`, `docs/planning/`, or tests into this feature branch: those belong to `codex/travel-planning`. B02 exposes optional hooks; before that branch is merged, the Planning action is disabled and the campus model adapter check records `MODEL_ADAPTER_NOT_INSTALLED` if credentials exist. The synthetic B03 quote examples are data fixtures, not copied Planning source. Later merge both PRs into a common `main` and run integration regression tests.
