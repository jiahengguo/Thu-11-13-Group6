# TripMate AI

[English](README.md) | [简体中文](README.zh-CN.md)

TripMate AI is an ELEC5620 project exploring whether one human founder can operate a useful travel service with four collaborating AI agents. The project focuses on Australian domestic trips and uses simulated supplier, booking, payment, and disruption data.

The current priority is **Stage 1: requirements, architecture, and system modelling**, due **24 September 2026**. A working prototype is planned for Stage 2.

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

## Planned system shape

```text
Traveller / Operator
        |
    Web interface
        |
  Orchestrator/API
        |
  +-----+----------------+-------------------+--------------------+
  | Operations Agent    | Travel Planning   | Customer Exception | Supplier Partnership
  +-----+----------------+-------------------+--------------------+
        |
  Reviewer / Guardrail
        |
  Tool adapters, repositories, trace store, and approval queue
```

The Stage 2 proof of concept is expected to use a small web interface, structured agent outputs, deterministic validation tools, and a simple traceable data store. The implementation stack will be finalised after the Stage 1 models are stable.

## Documentation

- [Stage 1 plan](docs/Stage1_Modeling_Task_List.md): deliverables, four-agent ownership, modelling rules, sequence, and completion checks.
- [Current project requirement](https://unisydneyedu-my.sharepoint.com/:w:/r/personal/jguo9172_uni_sydney_edu_au/_layouts/15/doc.aspx?sourcedoc=%7Bdb7e1c58-8a31-419c-a0cf-9058e8145514%7D&action=edit): the current product-requirement baseline.
- [Stage 1 marking criteria](docs/ELEC5620_Project_Stage_1_Marking_Criteria.pdf): assessment requirements and individual/group deliverables.

The README deliberately stays at project-overview level. Detailed requirements, use cases, model ownership, and submission checklists belong in the Stage 1 plan or assessed report, not here.

## Current scope

Stage 1 covers the requirement baseline, agent roles, use cases, architecture, UML models, traceability, presentation, and contribution evidence. Stage 2 will implement a demonstrable subset of these models. Real bookings, payments, advertising publication, and supplier contracts are outside the prototype.

## Contributing

Keep requirement IDs, use-case IDs, and diagram IDs stable. Changes to an agent's scope should be reflected first in the current project requirement, then in the Stage 1 plan and affected models. Record individual contributions through commits, pull requests, and the final contribution table.

## Course notice

TripMate AI is an educational feasibility prototype for ELEC5620. It is not a live travel agency or booking service.
