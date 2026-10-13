# B02/B03 branch and integration notes

Verified on Windows, 2026-10-13.

## Local directories

- `repo`: earlier mixed working directory. Its `feature/b02-b03-jason` branch
  starts at Planning commit `a7d13e5`, and has uncommitted older B02/B03 files.
  These files were preserved, not used as the final clean branch.
- `supplier-partnership`: B02/B03 changed-files package, updated with the Windows
  SQLite connection-release fix and current documentation.
- `supplier-partnership-branch`: full baseline checkout on
  `feature/b02-b03-jason-clean`, based on team main `f7a61ed`.

The clean branch includes only B02/B03 changes and shared README/configuration
updates. It does not include Moore's Planning implementation or change shared
contract schemas, agent implementations or their service ports.

## Actual merge check with Planning

A temporary checkout of `origin/codex/travel-planning` was merged with the clean
B02/B03 branch. There were no source-code conflicts. Three common files conflict:

- `.env.example`: keep the B02 FIXTURE default and SQLite setting, plus the
  campus provider/model/key-placeholder fields needed by Planning. Never put
  a personal credential into this file.
- `README.md`: keep Moore's runbook/API links and the current B02/B03 startup
  instructions. Replace old statements saying the web/database are unimplemented.
- `README.zh-CN.md`: retain the same information in Chinese.

`pyproject.toml` merges automatically, retaining Planning's `tzdata` dependency
and B02/B03 static/JSON package data. Do not replace the entire integrated file
with the version from the changed-files package.

After resolving the common-file conflicts, all **82 tests** and **20 contract
examples** passed. A source comparison confirmed Planning and campus-adapter
code remained unchanged. Resolved common-file examples were saved locally in
`tmp/b02-b03-review/merge-resolutions` for reference.

## Completion status

B02 application/database/configuration, recorded LLM blocker and labelled
fixture mode are implemented and checked locally. B03 scenario coverage,
repeatable reset, relationships and preservation of shared records are checked.

Moore/another teammate still needs to review and reproduce a clean checkout;
the project still needs shared integration and evidence attachment before
both cards satisfy their shared Definition of Done. No remote push or main
merge is claimed by this verification.
