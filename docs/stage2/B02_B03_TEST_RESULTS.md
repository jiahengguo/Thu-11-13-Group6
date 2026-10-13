# B02/B03 verification record (2026-10-13, Windows)

Owner: Jason. Verified against team main `f7a61ed` and Planning `a7d13e5`.
Python: 3.12.14. No real campus model request or remote write was performed.

## Verified locally

- Team main plus only B02/B03 files: **25/25 tests pass**.
- Planning plus B02/B03: **82/82 tests pass**.
- Shared contract examples: **20/20 pass**.
- Frontend JavaScript syntax: PASS.
- Wheel build and installation into a separate target directory: PASS.
- Installed package (not source tree): static HTML/JS/CSS, HTTP status,
  SQLite connectivity, fixture catalog and token-protected reset: PASS.
- Two resets restore identical fixture data; foreign keys pass; failed fixture
  reseeding rolls back; shared non-fixture records survive reset.
- Optional Planning demo uses a separate database. Windows testing found an
  unclosed reset connection; `contextlib.closing` now releases it explicitly.
- No API key: smoke check persists BLOCKED/MODEL_NOT_CONFIGURED without secrets.

The installed-package check used an existing Python environment with the shared
JSON-schema dependency already installed. It proves packaged resources are
present; it does not replace another member reproducing a fresh environment.

## Branch and delivery

`feature/b02-b03-jason-clean` is based directly on team main, not on Moore's
Planning commit. The changed-files delivery requires the team baseline.
Merge common files rather than blindly replacing an integrated repository;
retain Planning's `tzdata` dependency when Planning is merged.

## Remaining Definition of Done evidence

- Moore/team member review and independent clean-checkout startup.
- Shared integration and attached evidence in Jira/PR.
- Real campus model smoke when a personal key and campus/VPN access are available;
  until then the recorded blocker is the B02-AC3 result.

B02/B03 implementation is verified locally. Neither card is claimed fully Done
until the shared review, integration and reproduction requirements are met.
