# Operations acceptance evidence

Date: 13 October 2026 (Australia/Sydney). Branch: `operations-agent`. Base: `1c83d8d`.

## Main-based regressions

```sh
.venv/bin/python -m unittest discover -s tests -v
```

65 tests passed: 25 existing B01/B02/B03 checks plus 40 Operations/HTTP/analytics tests.
Coverage includes confirmation/split and required fields, unverified/cross-user access,
Free count/five-versus-six days, Paid expiry, member-offer eligibility, routine enquiry,
absent/mismatched/failed specialists, response review and scoped decisions, material edits,
durable delivery and its failure/retry states, atomic trace rollback, replay/stale versions,
two explicit human requests, history snapshots, restart/reset preservation, safe model
extraction and redaction, bounded dependency waiting/late-result blocking, same-database
Reviewer callbacks, and zero-denominator/same-cohort metrics.

HTTP tests require permission to bind localhost in a restricted execution environment.
They were run with that access; no test was skipped or treated as passing merely because
network access was unavailable.

## Independent PR #9 compatibility

Planning source was read from a clean archive of `origin/codex/travel-planning` at
`a7d13e589d1b6398259394baf1719f8d2da6fd1a` in a temporary directory. It was not
merged/copied into the Operations branch.

```sh
git archive origin/codex/travel-planning | tar -x -C /tmp/tripmate-planning-integration
.venv/bin/python scripts/verify_operations_planning.py \
  --planning-source /tmp/tripmate-planning-integration
```

Create the empty temporary directory first. After both modules are merged, run the
script without `--planning-source` against the installed package.

7 checks passed using **actual Planning code**, B03 synthetic offers, implemented
Operations access/entitlement and an explicitly named test Reviewer:

1. Shared-database generation, exact response review/delivery and separate adoption.
2. Unreviewed proposal and missing explicit acceptance blocked.
3. Immutable baseline, confirmed budget/constraint changes and field-level comparison.
4. Free two-trip revision/adoption uses scoped membership and retains two distinct trips.
5. Internal supplier costs, quote snapshots and LLM drafts omitted from public reads;
   another traveller cannot read the plan.
6. Expired/changed quote and stale selected-baseline adoption rejected.
7. Operations audit failure after canonical adoption preserves the correct trip count;
   retry completes audit without a second adoption.

The default B03 scenario returned a validated AUD 517.00 proposal. This is simulated
business execution, not a live supplier quote or booking. The Reviewer is a test substitute,
not a claim that B10 is integrated.

## Browser checks

Local preview: `/operations` on the B02 server, using a separate temporary SQLite file.
Checked the rendered confirmation summary and checkbox gate, routine response staying
hidden until recorded delivery, CLOSED state after delivery, Paid map access with selectable
schematic route points, missing-model/Planning controls, and preservation of cases across a
server restart. The desktop layout was visually inspected. Automated HTTP checks independently
cover session identity, direct request rejection and protected reads.

## Additional checks and limits

`git diff --check`, Python compilation and all original contract examples pass.
No personal `.env`, credential, runtime database or unrelated `.DS_Store` change belongs
in the branch commit.

No live campus model call, production authentication, automatic Supplier/Exception handling,
live map, discounted Planning quote or four-agent group acceptance is claimed. Those
dependencies stay explicit in the interface and handoff. Teammate review/clean-start
reproduction remains pending.
