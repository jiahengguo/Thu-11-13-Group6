# TripMate AI

**Authenticated portals branch (13 October 2026):** `portal-supabase-integration`
adds a public website and separate Traveller `/app`, Supplier `/supplier`, and
Operator `/admin` portals. Supabase Auth verifies real accounts; backend role and
ownership checks protect private cloud Operations records. The default web entry
now runs authenticated portals. The B02/B03 role-switching workbench requires
explicit `--workbench` and remains isolated development tooling.

```sh
python -m pip install -e .
# Configure the new project's keys in the ignored .env; apply migrations first.
python -m tripmate.portal.server --port 8780
```

See [portal setup and boundaries](docs/portal/PORTAL_HANDOFF.md) and
[portal verification](docs/portal/TEST_RESULTS.md). Auth and cloud persistence are
real; specialist travel processing and financial transactions retain the report's
prototype boundaries. Do not treat a portal deployment as four-agent completion.

**Operations Agent branch (13 October 2026):** Run the existing local server and open
`/operations` for confirmed request intake, simulated membership/access checks, tracked
case coordination, operator review and controlled response delivery. See the
[Operations handoff](docs/operations/OPERATIONS_HANDOFF.md) and
[acceptance evidence](docs/operations/TEST_RESULTS.md). Planning/Supplier/Exception and
automatic Reviewer dependencies remain explicitly injected; this branch does not merge
the separate Travel Planning PR or claim four-agent completion.

**Supplier Partnership B02/B03 branch (13 October 2026):** Local-only Web API/SQLite foundation, replayable synthetic supplier/traveller/disruption fixtures, controlled reset, and a model-smoke endpoint have been added. [Handoff](docs/stage2/B02_B03_HANDOFF.md). Four-agent workflows are **not** integrated. Planning demonstrations and campus model integration are enabled only after their separate provider implementation is merged; until then, the page reports them as unavailable.

[English](README.md) | [简体中文](README.zh-CN.md)

TripMate AI is an ELEC5620 project exploring whether one human founder can operate a useful travel service with four collaborating AI agents. The project focuses on Australian domestic trips and uses simulated supplier, booking, payment, and disruption data.

The Stage 1 report is the design baseline. **Stage 2 B01 now has a shared contract and modular project framework**, pending four-member review. B02 provides a local-only Web/API and SQLite workspace; a real campus LLM check requires the separately supplied provider adapter and network/credentials.

Start with the [project framework and local checks](#project-framework), [v1.0.0 contracts](docs/contracts/v1/CONTRACTS.md), [requirement mapping](docs/contracts/v1/REQUIREMENT_MAPPING.md), and [B01 acceptance record](docs/contracts/v1/B01_ACCEPTANCE.md).

## Product idea

Travel planning is fragmented across transport, accommodation, activities, prices, weather, and policies. TripMate AI combines these inputs into feasible itinerary options, explains trade-offs, revises plans when circumstances change, and keeps a human operator responsible for high-impact decisions.

The system is a One-Person AI Company rather than a single travel chatbot. Each team member owns one agent direction:

| Agent | Business responsibility |
| --- | --- |
| Operations Agent | Customer acquisition, front-desk service, intent collection, membership checks, and routing |
| Travel Planning Agent | Transport, accommodation, and activity planning; constraint checking; comparison and revision |
| Customer Exception Agent | Disruption recovery, complaint handling, evidence gathering, and escalation |
| Supplier Partnership Agent | Supplier offers, inventory terms, price and margin validation |

A shared Reviewer/Guardrail checks constraints, evidence, pricing, policy, and approval requirements. The human founder/operator supervises the company and makes decisions that should not be delegated.

## Core workflow

1. The Operations Agent receives a lead or customer request, collects missing information, checks membership rules, and routes the case.
2. The Travel Planning Agent retrieves eligible offers and builds complete itinerary options.
3. Deterministic tools validate budget, timing, availability, price, margin, and other hard constraints.
4. The Reviewer/Guardrail checks the proposal before it is shown to the traveller.
5. The Customer Exception Agent handles disruptions or complaints and asks for human review when necessary.
6. The system records decisions, tool results, plan versions, costs, and outcomes for evaluation.

## Product baseline

- Initial scenario: a short Sydney-to-Melbourne trip.
- Travel modes: Comfort, Value, and Budget.
- Free membership: at most two simultaneous planned or active trips and five days per trip; labelled advertising may be shown.
- Paid membership: no free-tier trip-count or duration limit, no advertising, and access to route maps and approved premium features.
- Revenue model: supplier margin, paid membership, and advertising for free users.
- Human approval remains required for real publication or spending, supplier commitments, payments, refunds or compensation, and other high-impact actions.

## Project framework

The framework follows the Stage 1 report's four-agent architecture, UC-01–UC-08,
G-04/G-05 and the B01 shared-contract requirements. The 10 October 2026 delivery
covers contracts and module boundaries. Python 3.9+ is the backend skeleton's
implementation choice; the report does not prescribe a language. B02 now provides
a local HTTP/static frontend and SQLite workspace, and B03 provides resettable
synthetic fixtures. A real model check requires the separately merged campus
adapter, a local key and campus/VPN access. Four-agent business integration is pending.

### Application structure

```text
Traveller / Supplier                    Human Founder / Operator
        |                                           |
        +------ Shared web interface: intake, plans, operator workspace [B02]
                              |
                     API / Orchestrator
                              |
                    Operations (Jiaheng)
                 +------------+-------------+
          Planning (Moore) Exception (wrd) Supplier (Jason)
                 +------------+-------------+
                Shared Reviewer / Guardrail (wrd)
                              |
           Entitlement/access, constraints, pricing, LLM/tool adapters
                              |
                One database, trace and human approval records
```

The four agents are internal modules in one application. Operations confirms
requests, coordinates work and delivers external responses. Specialists return
proposals rather than independently making commitments to Travellers. The
Reviewer is a shared control service, not a fifth business agent. Human
assistance, scoped approval and real transaction execution are distinct concepts.

```text
src/tripmate/
  __main__.py          Framework inspection and JSON example validation
  orchestrator.py      Composition root for the four agents
  agents/              Member-owned modules and shared handle_case protocol
  contracts/           Schema loader, validator and v1/schemas.json
  services/ports.py    Entitlement, constraint, pricing, review and access ports
  adapters/ports.py    LLM and approved-offer lookup ports
  persistence/ports.py Trace and approval repository ports
  api/                 B02 HTTP boundary
api/static/            B02 frontend assets (inside src/tripmate/)
docs/
  contracts/v1/        Contracts, mappings, review evidence and JSON examples
tests/                 B01 success and rejection-path tests
```

These ports are unimplemented protocols. They do not save data or call models.
Agent stubs return `executionMode=STUB`, `status=FAILURE` and `NOT_IMPLEMENTED`.
FIXTURE in the JSON examples identifies synthetic contract messages, not business
results executed by the application.

### Local checks

Run from the repository root. Initial dependency installation requires network
access. Configuration templates contain no credentials.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e .
.venv/bin/python -m tripmate
.venv/bin/python -m tripmate --validate-examples docs/contracts/v1/examples
.venv/bin/python -m unittest discover -s tests -v
```

If the project itself is not installed, install `jsonschema[format]>=4.23,<5`
and prefix the last three commands with `PYTHONPATH=src`. The B02 server reads
`.env`; the framework-inspection CLI does not. Start the workbench with
`python -m tripmate.api.server --workbench --port 8765`. B02 supports FIXTURE and STUB business
modes; use the separate model-smoke action to record a live call or its blocker.

### B01 deliverables

- [Contracts v1.0.0](docs/contracts/v1/CONTRACTS.md): fields, states, errors, evidence and approval semantics.
- [Requirement mapping](docs/contracts/v1/REQUIREMENT_MAPPING.md): requirements, use cases, owners and confirmed/unresolved PLAN/TP relationships.
- [B01 acceptance record](docs/contracts/v1/B01_ACCEPTANCE.md): actual test evidence and pending member reviews.
- [Schema bundle](src/tripmate/contracts/v1/schemas.json): language-neutral machine-readable contracts.

Public schemas reject unknown fields and require explicit sources, validation
results, errors and approval flags. Money uses two-decimal AUD strings; timestamps
must include a timezone. Schema validation does not establish budget, inventory,
entitlement, offer expiry, margin or itinerary feasibility. Implement those rules
in B04/B07/B08/B09.

### Member handoff

| Owner | Next work |
| --- | --- |
| Jiaheng | B06 creates Cases after confirmation; B07 adds entitlement/access and controlled external responses |
| Moore | B04 deterministic validation; B09 planning; keep version assessment separate from trip lifecycle |
| wrd | B05 persisted trace; B10 review and human approval scoped to subject version and authority |
| Jason | B02 shared web/backend/database/LLM; B03 simulated fixtures; B08 offers and B16 campaigns |

Preserve caseId/correlationId/sourceReferences and validate inputs and outputs.
Report failed saves explicitly. Approvals must match the current subject version;
material changes require fresh review and approval. B04 must document the rounding
tie rule left unspecified by the report. Example amounts are not global policies.

B01 code and documentation are ready for review. All four member confirmations
remain pending, so B01 cannot yet be marked Done.

## Documentation

- [Stage 1 plan](docs/Stage1_Modeling_Task_List.md): deliverables, four-agent ownership, modelling rules, sequence, and completion checks.
- [Current project requirement](https://unisydneyedu-my.sharepoint.com/:w:/r/personal/jguo9172_uni_sydney_edu_au/_layouts/15/doc.aspx?sourcedoc=%7Bdb7e1c58-8a31-419c-a0cf-9058e8145514%7D&action=edit): the current product-requirement baseline.
- [Stage 1 marking criteria](docs/ELEC5620_Project_Stage_1_Marking_Criteria.pdf): assessment requirements and individual/group deliverables.

The README contains the project overview, framework, startup and handoff instructions. Detailed contracts, requirement mappings and acceptance evidence remain in docs/contracts/v1.

## Current scope

Stage 1 covers the requirement baseline, agent roles, use cases, architecture, UML models, traceability, presentation, and contribution evidence. Stage 2 will implement a demonstrable subset of these models. Real bookings, payments, advertising publication, and supplier contracts are outside the prototype.

## Contributing

Keep requirement IDs, use-case IDs, and diagram IDs stable. Changes to an agent's scope should be reflected first in the current project requirement, then in the Stage 1 plan and affected models. Record individual contributions through commits, pull requests, and the final contribution table.

## Course notice

TripMate AI is an educational feasibility prototype for ELEC5620. It is not a live travel agency or booking service.
