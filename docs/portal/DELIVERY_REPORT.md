# TripMate portal and Supabase delivery

Delivered on 13 October 2026 in `portal-supabase-integration`.
Supabase project: `bkfqklqxjcjbcstpyqxo`.

## Result

The default web application now provides a public website and three authenticated
role workspaces instead of a shared simulation role picker. Supabase verifies real
accounts and stores Operations records in a protected cloud database. The existing
Operations coordinator remains responsible for confirmed intake, routing, reviewed
responses and traceable closure.

| Requested outcome | Delivered behavior | Evidence |
| --- | --- | --- |
| Separate branch without a codex prefix | `portal-supabase-integration`, based on the Operations implementation | Git branch and pull request |
| Unified website | `/` introduces the service, membership rules and partner entry | Browser inspection, desktop and 390px mobile |
| Real login | Email/password registration, email verification, login, token refresh, logout and recovery interface | 88 regression tests; real Supabase login checks; owner-confirmed registration/verification |
| Traveller portal | `/app`: confirmed requests, own cases/support, membership and saved-trip list | Actual browser request-to-delivery scenario |
| Supplier portal | `/supplier`: supplier-only categories and own offer/request workspace; reviewed application prerequisite | Real atomic onboarding test and browser inspection |
| Internal portal | `/admin`: case queue, review decisions, response release and supplier applications | Operator browser inspection and real cloud delivery test |
| Permission isolation | Server-protected HTML/APIs, role/ownership checks, protected profile and private business schema | Cross-owner/role tests, direct REST/RPC rejection, seven RLS-enabled tables |
| Correct cloud project | New project configured locally; migrations applied only there | Service connection and database inspection |
| Internal access for owner | Owner self-registered and verified; audited Operator grant completed | Trusted provisioning RPC returned success |
| Jira Backlog | WN5620-31–38: eight English Stories with User Story, acceptance criteria and report references | Backlog inspection; no sprint; To Do; assigned to jiaheng guo |
| Handoff documentation | Setup, security boundaries, tests and Jira mapping committed | Documents listed below |

## Read and run

- [Setup and implementation boundaries](PORTAL_HANDOFF.md).
- [Verification record](TEST_RESULTS.md).
- [Jira Stories and acceptance criteria](JIRA_BACKLOG.md).

```sh
python -m pip install -e .
# Set this project's keys in the ignored .env and apply migrations.
python -m tripmate.portal.server --port 8780
```

Open `http://127.0.0.1:8780/`. Sign in at `/login`; server-assigned access chooses the
appropriate portal. The default `tripmate.api.server` entry delegates to the portals.
The legacy development workbench requires explicit `--workbench` and stays outside
any public deployment.

## Validation and delivery boundaries

All 88 regression tests and 16 real Supabase integration checks passed. JavaScript
syntax, Python compilation and Git whitespace checks passed. Public and role-specific
pages were inspected in Chrome. Case confirmation, processing, checked inbox delivery
and closure were completed against the real database using synthetic requests.

The owner requested retaining the five synthetic QA accounts. Their access remains
active; no ban or deletion was performed. Their random credentials are not committed
or published. Real user secrets remain in the ignored local configuration, and the
owner's login email is not included in the public handoff.

This delivery provides real identity, authorization and cloud persistence with a
local runnable app. It does not deploy a public production website or complete the
separate specialist agents. Missing dependencies escalate explicitly. Offer assessment,
itinerary generation/comparison/adoption screens, shared supplier organizations,
production sessions/pagination and external hosting remain integration/deployment
work. WN5620-38 records the production follow-up. Bookings, payments, refunds,
contracts and advertising publication remain simulated/outside scope as in report §13.

The pull request into main includes the Operations coordinator foundation because
that published implementation is required by the portals and is not yet in main.
