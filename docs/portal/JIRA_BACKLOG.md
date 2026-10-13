# Portal and Supabase Jira Backlog

Created on 13 October 2026 in project WN5620. All eight entries are Stories assigned to jiaheng guo, with no sprint selected. Status remains To Do pending planning/review. Implementation branch: `portal-supabase-integration`.

## [WN5620-31](https://elec5619-5-group-1.atlassian.net/browse/WN5620-31) — [PORTAL-FR] Add verified Supabase registration, sign-in and account recovery

User Story
As a traveller, I want to register, verify my email, sign in and recover my account so that my travel requests are linked to a trusted identity.

Acceptance Criteria
1. New registrations receive Traveller/Free access regardless of user-editable metadata; no public role selector is available.
2. Unverified accounts and invalid passwords cannot enter a protected portal.
3. Login/callback rotate the browser session; refresh and logout work without exposing provider tokens.
4. Recovery and verification callbacks validate provider identity and a browser-bound state; invalid or expired links give actionable guidance.

Report Alignment and Dependencies
UC-05 identity/access preconditions; report §§2.1–2.2. Real Auth integration replaces simulation identity selection. Owner inbox verification remains required for the initial Operator account.

Implementation Reference
Branch: portal-supabase-integration
https://github.com/jiahengguo/Thu-11-13-Group6/tree/portal-supabase-integration
Supabase project: bkfqklqxjcjbcstpyqxo
Review docs/portal/PORTAL_HANDOFF.md and docs/portal/TEST_RESULTS.md. Keep in Backlog without a sprint until planned; branch delivery is not a merged/released status.

## [WN5620-32](https://elec5619-5-group-1.atlassian.net/browse/WN5620-32) — [PORTAL-FR] Build the public website and isolated Traveller workspace

User Story
As a traveller, I want a clear website and a private travel workspace so that I can submit confirmed requests and follow their progress without seeing internal business controls.

Acceptance Criteria
1. The public website presents product workflow, Free/Paid rules, customer sign-in and a supplier application entry.
2. Only Traveller accounts can access /app; its navigation covers requests/support, trips, planning, membership and account details.
3. A structured summary is editable and explicitly confirmed before a CustomerCase is created.
4. Own-case views display required information, safe progress, human assistance/withdrawal actions and formally delivered responses; internal drafts are absent.
5. Missing specialists produce an honest waiting/escalation state; no completed itinerary or booking is fabricated.

Report Alignment and Dependencies
Report §§3.1–3.2, UC-05 and UC-07. Relates to WN5620-7, WN5620-8 and WN5620-24; this story supplies the authenticated frontend rather than duplicating agent algorithms.

Implementation Reference
Branch: portal-supabase-integration
https://github.com/jiahengguo/Thu-11-13-Group6/tree/portal-supabase-integration
Supabase project: bkfqklqxjcjbcstpyqxo
Review docs/portal/PORTAL_HANDOFF.md and docs/portal/TEST_RESULTS.md. Keep in Backlog without a sprint until planned; branch delivery is not a merged/released status.

## [WN5620-33](https://elec5619-5-group-1.atlassian.net/browse/WN5620-33) — [PORTAL-FR] Add reviewed supplier onboarding and a separate partner portal

User Story
As a travel service provider, I want to apply for verified supplier access and use a private partner workspace so that my offers and cooperation requests can be reviewed through Operations.

Acceptance Criteria
1. Traveller accounts can submit company details and a cooperation proposal without self-assigning Supplier access.
2. Only an Operator can approve/reject a pending application with a recorded reason; approval and role change commit together.
3. Approved Supplier accounts enter /supplier with supplier-only request categories and account-owned records.
4. Offer requests capture product reference, quantity, AUD supplier price, validity, cancellation terms and source before confirmation.
5. Submission/application approval is clearly distinguished from approved inventory, a binding agreement or a real transaction.

Report Alignment and Dependencies
Report §§2.5 and 3.5; UC-05/UC-06. Relates to WN5620-9. First version has one supplier account owner; shared company membership and normalized specialist offer storage remain integration work.

Implementation Reference
Branch: portal-supabase-integration
https://github.com/jiahengguo/Thu-11-13-Group6/tree/portal-supabase-integration
Supabase project: bkfqklqxjcjbcstpyqxo
Review docs/portal/PORTAL_HANDOFF.md and docs/portal/TEST_RESULTS.md. Keep in Backlog without a sprint until planned; branch delivery is not a merged/released status.

## [WN5620-34](https://elec5619-5-group-1.atlassian.net/browse/WN5620-34) — [PORTAL-FR] Provide an authenticated Operator queue and reviewed response release

User Story
As the human operator, I want a separate work queue with evidence and approval controls so that I can supervise cases and release only checked responses.

Acceptance Criteria
1. Only an active, verified Operator can access /admin and its review APIs.
2. The queue shows open cases, human-assistance cases and responses ready for delivery.
3. Case details show confirmed fields, internal evidence/trace and review context; decisions include Approve, Request revision, Reject or Take over with reasons.
4. Checked response delivery records the actual Operator identity, writes the requester inbox and closes the case atomically.
5. Failure, revision, withdrawal and closure remain visible; a failed dependency cannot be bypassed by claiming approval.

Report Alignment and Dependencies
Report §§2.6 and 3.6; UC-05. Relates to WN5620-11, WN5620-22 and WN5620-23. Trusted Operator provisioning requires an explicitly authorised, existing verified account.

Implementation Reference
Branch: portal-supabase-integration
https://github.com/jiahengguo/Thu-11-13-Group6/tree/portal-supabase-integration
Supabase project: bkfqklqxjcjbcstpyqxo
Review docs/portal/PORTAL_HANDOFF.md and docs/portal/TEST_RESULTS.md. Keep in Backlog without a sprint until planned; branch delivery is not a merged/released status.

## [WN5620-35](https://elec5619-5-group-1.atlassian.net/browse/WN5620-35) — [PORTAL-NFR] Persist Operations state, traces and retries atomically in Supabase

User Story
As an operator, I want cloud records, decision traces and retry results to remain consistent so that a failed save or repeated action cannot corrupt a customer or supplier case.

Acceptance Criteria
1. Cases/intakes, inbox delivery, traces and command results are persisted in the private Supabase schema.
2. A stale database revision rejects the entire transaction; callbacks are not automatically replayed.
3. Identical command retries return the saved result; changed content with the same key is rejected.
4. Cloud outages show no success or false closure, and partial writes are absent.
5. Migrations and setup document the correct project, manual dashboard application and the snapshot adapter workload limit.

Report Alignment and Dependencies
UC-05 trace/delivery rules; report §13. Extends WN5620-26 and WN5620-27 to actual cloud storage. Current snapshot adapter is for teaching-scale traffic, with production query pagination deferred.

Implementation Reference
Branch: portal-supabase-integration
https://github.com/jiahengguo/Thu-11-13-Group6/tree/portal-supabase-integration
Supabase project: bkfqklqxjcjbcstpyqxo
Review docs/portal/PORTAL_HANDOFF.md and docs/portal/TEST_RESULTS.md. Keep in Backlog without a sprint until planned; branch delivery is not a merged/released status.

## [WN5620-36](https://elec5619-5-group-1.atlassian.net/browse/WN5620-36) — [PORTAL-NFR] Enforce real-account authorization and protect internal data

User Story
As a customer or supplier, I want my records isolated from other accounts and internal company data so that using the service does not expose private information.

Acceptance Criteria
1. Every protected HTML route and API verifies Supabase identity plus active database role; client metadata, role headers and requester IDs cannot grant access.
2. Cross-role and cross-owner reads/writes are rejected; deactivation and role changes affect subsequent requests.
3. All new tables enable RLS; authenticated accounts can only read their own public profile and cannot update role or membership.
4. Private schema and business RPCs reject anonymous and ordinary authenticated JWTs; server secrets never reach static files or Git.
5. External responses omit internal drafts, approval snapshots and internal pricing; tests cover forged identities and direct REST/RPC attempts.

Report Alignment and Dependencies
UC-05 authentication/access rules. Extends WN5620-25 from simulated profiles to verified Supabase identities and database privileges.

Implementation Reference
Branch: portal-supabase-integration
https://github.com/jiahengguo/Thu-11-13-Group6/tree/portal-supabase-integration
Supabase project: bkfqklqxjcjbcstpyqxo
Review docs/portal/PORTAL_HANDOFF.md and docs/portal/TEST_RESULTS.md. Keep in Backlog without a sprint until planned; branch delivery is not a merged/released status.

## [WN5620-37](https://elec5619-5-group-1.atlassian.net/browse/WN5620-37) — [PORTAL-NFR] Secure sessions and make portal interactions accessible

User Story
As a portal user, I want secure sessions and clear, accessible interactions so that I can use the service reliably on desktop or mobile.

Acceptance Criteria
1. Cookies are HttpOnly/SameSite and Secure under HTTPS; provider access/refresh tokens remain server-side.
2. Writes enforce exact Origin, session CSRF, request-size/type limits and rate limits; pages use no-store and restrictive CSP.
3. Logout/expiry reject reused sessions; email callbacks reject a mismatched browser state.
4. Forms use labelled controls, visible keyboard focus, live error/status messages and explicit confirmation.
5. Layouts remain usable at a mobile viewport and respect reduced-motion preferences; errors identify the next action.

Report Alignment and Dependencies
UC-05 controlled external interface; non-functional implementation requirements. Relates to WN5620-19 and WN5620-20; includes browser acceptance evidence on the portal branch.

Implementation Reference
Branch: portal-supabase-integration
https://github.com/jiahengguo/Thu-11-13-Group6/tree/portal-supabase-integration
Supabase project: bkfqklqxjcjbcstpyqxo
Review docs/portal/PORTAL_HANDOFF.md and docs/portal/TEST_RESULTS.md. Keep in Backlog without a sprint until planned; branch delivery is not a merged/released status.

## [WN5620-38](https://elec5619-5-group-1.atlassian.net/browse/WN5620-38) — [PORTAL-NFR] Prepare production hosting and scalable session/storage operations

User Story
As the service operator, I want a controlled HTTPS deployment with reliable session and storage infrastructure so that verified users can access the portals beyond a single local process.

Acceptance Criteria
1. Deploy the portal behind HTTPS with one exact configured public origin and the matching narrow Supabase callback allowlist.
2. Keep the development workbench, reset endpoints and simulation role selector outside the public deployment.
3. Replace in-memory sessions with protected shared sessions before multiple app instances are used.
4. Replace whole-store snapshots with targeted/paginated database queries and validate concurrent workloads.
5. Verify email delivery/recovery, secret configuration, monitoring, migrations and restart behavior in the deployed environment; document remaining specialist dependencies.

Report Alignment and Dependencies
Follow-up delivery story. The branch currently runs locally and does not claim a production deployment, multi-instance operation or completed four-agent integration. Report §13 still excludes real financial/travel transactions.

Implementation Reference
Branch: portal-supabase-integration
https://github.com/jiahengguo/Thu-11-13-Group6/tree/portal-supabase-integration
Supabase project: bkfqklqxjcjbcstpyqxo
Review docs/portal/PORTAL_HANDOFF.md and docs/portal/TEST_RESULTS.md. Keep in Backlog without a sprint until planned; branch delivery is not a merged/released status.
