# Customer Exception Agent delivery backlog

Scope confirmed by the module owner on 13 October 2026. All five work items are
Subtasks assigned to the owner, under the existing project tasks. Jira inherited
Sprint 1 from the parents; the owner explicitly confirmed retaining that placement.
The original backlog-only wording in the creation descriptions is superseded by
this confirmation. Parent tasks and shared integration are not claimed complete.

| Work item | Parent | Report coverage | Deliverable |
| --- | --- | --- | --- |
| [WN5620-39](https://elec5619-5-group-1.atlassian.net/browse/WN5620-39) | WN5620-13 | EXC-01, EXC-AH-01, UC-03 | Simulated cancellation investigation and validated recovery options |
| [WN5620-40](https://elec5619-5-group-1.atlassian.net/browse/WN5620-40) | WN5620-16 | EXC-02, EXC-AH-02, UC-04 | Evidence-supported delay complaint recommendation or human referral |
| [WN5620-41](https://elec5619-5-group-1.atlassian.net/browse/WN5620-41) | WN5620-6 | AC-UC03-06, AC-UC04-07 | Durable source-linked local investigation records |
| [WN5620-42](https://elec5619-5-group-1.atlassian.net/browse/WN5620-42) | WN5620-11 | AC-UC03-03–05, AC-UC04-03–06 | Deterministic checks, simulated review and pending human approval boundaries |
| [WN5620-43](https://elec5619-5-group-1.atlassian.net/browse/WN5620-43) | WN5620-20 | UC-03/04 specialist acceptance criteria | English demo, runnable examples, verification and setup evidence |

The FR/NFR title prefixes follow the board's existing naming convention. They
classify implementation work; they do not introduce new report requirement IDs.

## Repository placement

- Base: `main`, commit `a1605f4a33ce3c65b653a85ba2629e276db776da`.
- Feature branch: `codex/customer-exception-agent`.
- Core module: `src/tripmate/exception_handling/`.
- Agent entry point: `src/tripmate/agents/exception.py`.
- Existing workbench integration: `src/tripmate/api/`.
- Verification: `tests/test_exception.py` and `docs/exception/TEST_RESULTS.md`.

EXC-O1, live TripMate AI integration, real human decisions and real transactions
are excluded. Shared trace/review/Operations composition still needs group
integration and review. A checked internal recommendation does not close a case.
