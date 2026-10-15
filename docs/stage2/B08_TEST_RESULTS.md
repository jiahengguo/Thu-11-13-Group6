# B08 Windows verification — 2026-10-13

Environment: Python 3.12.14, team main `f7a61ed`, B02/B03 Supplier branch,
and a separate combined test directory containing Planning `a7d13e5`.

## Results

- Supplier branch without B04: 42 tests discovered, 38 passed, 4 optional
  integration tests explicitly skipped because the Planning module is absent.
- Combined with actual B04/Planning: **99/99 passed** in approximately 22 seconds.
- B08 CLI with actual B04: coach assessment SUCCESS, one selectable offer,
  `modelExecution=FIXTURE_REPLAY`.
- Frontend script syntax: PASS.
- Wheel build and packaged Supplier modules/demo resources: PASS.

## Behaviour checked

- B03 six valid quotes and six negative/pending source examples.
- Exact configured price identity, ROUND_HALF_UP half-cent case, minimum margin,
  and rejection of a calculator that mutates or substitutes source cost.
- Missing fields, expiry boundary, zero/insufficient stock, USD, missing terms,
  mandatory charges and stale evidence reject selection with a recorded reason.
- LLM extraction cannot set approval/state fields or change independently
  verified source facts. Tests use a synthetic extractor, not a live model.
- Version-scoped review, persisted authorised human decision, scope and review
  matching; restricted terms remain pending without an explicit valid decision.
- Failed material revisions withdraw older approvals. Ownership remains locked
  after a failed revision. Fixture and real identities cannot be silently mixed.
- Late assessments cannot overwrite newer source versions. Trace/snapshot save
  failures produce failures and leave no selectable approved version.
- B08 offer/price/product bundles are consumed by Moore's unchanged Planning
  code and yield a successful simulated itinerary.
- HTTP assessment, repeated imports, pending approval, two resets, restored
  version 1 and preservation of shared Supplier records.

A final regression run exposed a Windows socket abort when a rejected POST
closed while its small request body remained unread. The local server now
discards a bounded body before sending its 403; the final combined suite passes.

## Limits and handoff

Planning code was used only in the separate combined verification directory,
not copied into this Supplier branch. B04 must be merged before the optional
Supplier demonstration can run. Production B05/B07/B10 adapters and Operations
runtime wiring remain team integration dependencies. No real campus AI call,
real approval, supplier commitment or remote push was performed.

Moore review, teammate reproduction and PR/Jira evidence remain necessary for
the shared Definition of Done. These tests verify implementation and explicit
fixture integration rather than completion of the four-agent application.
