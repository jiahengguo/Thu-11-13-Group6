# B01 acceptance and review record

Recorded: 10 October 2026 (Australia/Sydney).
Status: **ready for member review; not Done**.
Assignee: Jiaheng. Reviewer: wrd.

| Acceptance criterion | Delivered evidence | Status |
| --- | --- | --- |
| AC1: eight schemas approved by all four members | `src/tripmate/contracts/v1/schemas.json`; `CONTRACTS.md`; review table below | Schemas implemented and validated; four-member approval pending |
| AC2: examples retain caseId, correlationId, sources, validation, errors, requiresApproval | 20 `examples/*.json`, including four agents × success/failure/approval-pending | Automated schema validation passed |
| AC3: confirmed/unresolved PLAN/TP mapping and named owners | `REQUIREMENT_MAPPING.md`; four agent modules and composition root | Documented; semantic mapping and stack refinement await member review |

## Automated evidence

Commands executed from the repository root in a Python 3.9 virtual environment:

```bash
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
PYTHONPATH=src .venv/bin/python -m tripmate --validate-examples docs/contracts/v1/examples
```

Results: **13 tests passed; 20 JSON examples passed**. Editable package installation,
CLI startup, and installed schema-resource loading outside the repository also
passed. Negative tests cover
required fields on all eight public schemas, unknown fields/version, decimal
money/currency, invalid dates/timestamps, unconfirmed Cases, requester-kind
mismatch, missing error/approval fields, inferred approval, partial feasible
claims, unassessed approved offers and stubs falsely claiming success.

These are contract/interface checks, not evidence of business workflows,
persistence, real LLM execution, another member's startup reproduction or the
B04 deterministic validations. No Jira issue was updated by this implementation.

## Required human review

Each member should review the schemas, agent inputs/outputs, state refinement,
PLAN/TP mapping and the examples; record approval or requested changes with a
commit/PR/comment reference. Tests do not fill this table automatically.

| Member | Agent ownership | Decision | Evidence / date |
| --- | --- | --- | --- |
| Jiaheng | Operations; B01 assignee | Pending | — |
| Moore | Travel Planning | Pending | — |
| wrd | Customer Exception; B01 reviewer | Pending | — |
| Jason | Supplier Partnership; B02 | Pending | — |

Shared Definition of Done also requires peer review and shared integration.
Mark B01 Done only after those checks and all four schema approvals are recorded.
