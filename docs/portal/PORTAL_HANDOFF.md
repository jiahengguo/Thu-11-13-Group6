# Supabase authentication and role portals

Branch: `portal-supabase-integration`, based on the published Operations branch.
Project: `bkfqklqxjcjbcstpyqxo` (`https://bkfqklqxjcjbcstpyqxo.supabase.co`).
The superseded project `bpcjcsfwcgbradaxmmml` received no migration from this work.

## Run

```sh
python -m pip install -e .
python -m tripmate.portal.server --port 8780
# The existing default web entry delegates to the same authenticated portal:
python -m tripmate.api.server --port 8780
```

Copy `.env.example` to the ignored `.env`, obtain the publishable and existing server
secret for the correct project, and set `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`
and `SUPABASE_SECRET_KEY`. The server refuses missing cloud configuration or an
unapplied database migration. Keys are not embedded in static JavaScript or HTML.
The current workstation's ignored configuration has already been connected.

Apply `supabase/migrations/202610130001_portals.sql`, then
`202610130002_operator_bootstrap.sql` in the Supabase SQL editor on a fresh project.
Both have been applied to the named project. Tables were inspected: RLS is enabled
on all seven new tables. Migrations were applied through the dashboard, not the CLI;
repair/record those versions before later using CLI migration replay on this project.
Do not blindly rerun the initial table-creation migration on the configured database.

Supabase Auth URL Configuration for this local installation:

- Site URL: `http://127.0.0.1:8780/auth/callback`.
- Allowed redirect: `http://127.0.0.1:8780/auth/callback?state=*`.
- The callback state binds the email link to the browser session that requested it.
  Email confirmation can be followed by ordinary sign-in if a different browser is used;
  password recovery requires opening the email link in the requesting browser.

Open `/login` to register. New accounts receive **TRAVELLER / FREE** regardless of
user-editable auth metadata. Verify the email before signing in. Registration and
recovery depend on the project's configured email service and delivery limits.
This implementation does not disable Supabase email confirmation.

## Operator and supplier provisioning

Only a trusted server-side command can assign Operator access:

```sh
python -m tripmate.portal.admin --email AUTHORISED_VERIFIED_ACCOUNT_EMAIL
```

It requires an existing verified, active account and appends a private audit entry.
The owner explicitly authorised the initial Operator account;
the owner subsequently registered and verified that account, and Operator access
was assigned through the trusted audited RPC. No account was created or falsely
marked email-verified on their behalf.

A Traveller can apply to become a supplier using Company name and a service proposal.
An Operator reviews the application with a reason. Approval updates the account role
and application together in a database transaction. Rejection leaves Traveller access.
This first version assigns one portal role per account. Shared company workspaces,
multiple supplier employees and simultaneous Traveller/Supplier memberships are future
work; the implementation isolates supplier records by their verified account owner.
Supplier application approval is not approval of a travel offer or a contract.

## Routes and business views

| Route | Access and behavior |
| --- | --- |
| `/` | Public website: product workflow, membership rules and partner entry |
| `/login` | Verified password sign-in, Traveller registration, recovery request |
| `/auth/callback` | Validates provider tokens remotely, rotates opaque session; no tokens persist in browser storage |
| `/app` | Traveller request intake/confirmation, own cases, support, membership and saved-trip list |
| `/supplier` | Supplier offer/request submission, confirmation and own-case tracking |
| `/admin` | Operator queue, case evidence/trace, reviewed decisions, response release and supplier applications |

The HTML for protected portals is checked before serving it; APIs independently enforce
roles and ownership. Shared CSS/JavaScript is public and contains no protected records.
There is no simulation identity switcher or diagnostic endpoint in the portal server.
The legacy B02/B03 workbench remains a separate loopback development process, enabled
only with `python -m tripmate.api.server --workbench --port 8765`; never proxy it publicly.

Frontend form -> existing UC-05 Operations intake -> explicit confirmed summary ->
CustomerCase/SupplierCase -> existing routing/review/approval -> private checked inbox
and closure. The Operations coordinator remains the only external business gateway.
Provider drafts, membership snapshots, history snapshots and approval records are not
returned to external users. Supplier traces receive the same minimal event projection
as Traveller traces. Operator delivery now uses the verified Operator identity directly,
without impersonating the requester.

## Authentication and data boundaries

- Password login is sent to this project's Supabase Auth service. `/auth/v1/user`
  verifies the identity for every protected request; the app does not trust decoded
  client JWT claims, `user_metadata`, a requesterId body field or `X-Ops-Session`.
- Opaque cookies are HttpOnly, SameSite=Lax, Secure on HTTPS. Browser storage never holds
  provider access/refresh tokens. Sessions rotate on login/callback and expire after
  eight hours, with a one-hour idle timeout. Refresh tokens are server memory only.
- Account role/active status is read from the protected database on each HTTP request.
  Only request-scoped caching is used. Account deactivation and role changes affect
  subsequent requests. Logout destroys the local session even if provider logout fails.
- Writes require the exact configured Origin and a session CSRF token. Host checks,
  JSON/body limits, login/write rate limits, no-store and restrictive CSP are enabled.
- `public.tripmate_accounts` allows authenticated users to SELECT only their own row.
  Browser INSERT/UPDATE/DELETE grants are revoked. Roles and membership cannot be self-set.
- Case records, drafts, commands, traces and supplier applications are in the unexposed
  `tripmate_private` schema, with RLS and no anon/authenticated schema grants.
- Atomic business RPCs are executable only by `service_role`. The browser cannot call
  snapshot, commit, partner approval or operator provisioning directly, even with a valid JWT.
- Existing Operations callbacks use an optimistic global database revision and atomic
  writes/traces/idempotency results. Conflicts fail without replaying callbacks or partial
  persistence. The adapter retrieves a private server snapshot for the teaching workload;
  it is not yet a paginated, high-throughput production persistence design.

## Deployment and remaining agent work

The app runs locally on loopback by default. For deployment, place it behind an HTTPS
reverse proxy, set one exact `TRIPMATE_PUBLIC_ORIGIN`, forward that Host, and configure
the matching Supabase email callback allowlist. External HTTP origins are rejected.
There is no public hosting deployment in this change.

This is a single-process server with bounded in-memory authentication sessions. Restart
requires sign-in. A multi-instance deployment needs a protected shared session store,
a production web server, targeted/paginated storage, monitoring and deployment checks.

The identities, authentication and cloud persistence are real. The report's simulated
business scope remains: no real booking, charge, refund, signing or ad publication.
Planning/Supplier/Exception/Reviewer implementations are still explicit injected ports;
missing specialists cause documented human-assistance states, not invented results.
This branch does not claim complete itinerary generation, maps, offer approval or four-agent
integration. The portals expose intake and orchestration; specialist result screens must
be connected when those modules are merged. Supplier form fields currently serialize into
a confirmed details payload for the shared supplier request contract; normalized offer
storage and supplier assessment UI are subsequent integration work.

## Report alignment

Stage 1 §§2.1–2.7 and §§3.1–3.6 define actor boundaries. UC-05 defines authentication,
confirmed intake, coordination, review, human decisions and controlled delivery. UC-07
keeps entitlement deterministic. §13 keeps transactions simulated. The four route groups
are an implementation choice consistent with those boundaries, not specified report URLs.
