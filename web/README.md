# TripMate web portals

The default app is `tripmate.portal.server`, backed by Supabase Auth and private
cloud Operations storage. Its authenticated request queues use React; the rest of
the portal remains HTML/CSS/JavaScript in `src/tripmate/portal/static`.

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

## React integration

`src/RequestQueue.jsx` renders the shared queue for Traveller, Supplier and
Operator: case-ID/type search, status filters, clear filters, counts, loading and
failure messages, selected-case state and Operator metrics. The metrics count the
entire authorized queue, including cases hidden by filters. Search/filter state
survives a data refresh. Both backend review states share the `Under review`
filter. Busy commands disable React controls as well as the existing portal.

`src/queue-entry.jsx` exposes a small `TripMateQueue.mountQueue` bridge. The existing
portal loads server-authorized summaries and provides its guarded selection
callback. React owns only the marked queue and metrics mount points; legacy code
does not mutate them. The business forms, authentication, CSRF, ownership,
idempotency and approval boundaries remain on the existing backend. This is
incremental React adoption, not a complete SPA rewrite.

## Frontend development

Use Node 22.12+ (22.x) or a compatible newer supported LTS version. From this `web`
directory:

```sh
npm ci
npm test
npm run build
```

Versions are fixed in `package.json` and `package-lock.json`. Vite writes a
self-contained production IIFE to
`../src/tripmate/portal/static/portal-queue.js`; the build also copies React,
React DOM and Scheduler licenses into `portal-queue.LICENSE.txt`. Keep both outputs
with the source release and rebuild after frontend changes. The build leaves
other static assets intact and does not load application `.env` files.

All three authenticated HTML pages load the same local bundle before `portal.js`.
The Python server explicitly serves that asset under the existing self-only CSP.
No CDN, browser JSX compiler or frontend development server is used at runtime.

## Installation and release verification

The generated JavaScript and license are included in Python package data. Tutors
and teammates running a complete source ZIP use the existing root
`scripts/setup_demo.py` and `scripts/start_demo.py`; **Node and npm are not required
to install or run the packaged demo**. Internet access and valid Supabase/course
model settings remain necessary for the existing backend preflights.

Before accepting a changed release, run frontend tests/build and the complete
Python regression, then check clean installation, local bundle loading, all three
role queues, repeated-click behavior and existing planning/recovery flows. Unit
tests with provider doubles are not live-cloud business acceptance. The previously
accepted ZIP remains the baseline; React changes require their own acceptance.

CI and automatic release-ZIP delivery are separate follow-up tasks WN5620-63/64.
