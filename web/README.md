# TripMate web portals

The default app is now `tripmate.portal.server`, backed by Supabase Auth and private
cloud Operations storage. Static HTML/CSS/JavaScript lives in
`src/tripmate/portal/static`; no JavaScript build or framework is required.

- `/`: public website.
- `/login`, `/auth/callback`: registration, verified sign-in and account recovery.
- `/app`: authenticated Traveller workspace.
- `/supplier`: authenticated Supplier workspace.
- `/admin`: authenticated Operator workspace.

All protected HTML routes and APIs enforce server-derived roles. Requesters call
Operations, which coordinates specialist modules. No specialist agent is exposed
as an external browser endpoint. Shared styles do not share access rights.

See [setup and security boundaries](../docs/portal/PORTAL_HANDOFF.md).
The old `tripmate.api.server --workbench` is explicitly isolated development tooling;
never put it behind the public portal reverse proxy.
