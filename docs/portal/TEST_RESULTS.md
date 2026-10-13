# Portal acceptance evidence — 13 October 2026

Project: `bkfqklqxjcjbcstpyqxo`. Branch: `portal-supabase-integration`.

## Automated regression

88 tests passed, including the existing 65 Operations/B02/B03/contract tests and 23
new portal/repository checks. The new tests exercise real local HTTP requests with a
controlled Supabase substitute: server-protected HTML, cross-role and cross-owner
rejection, forged role fields/headers, verification, account revocation and role changes,
CSRF/Origin/Host, cookie rotation, logout/expiry, refresh, callback state, rate limiting,
atomic failure, CAS conflicts and idempotency. They do not prove external email delivery.
JavaScript syntax and Python compilation checks also passed.

## Real Supabase integration

Sixteen checks passed against the actual named project, using synthetic
`tripmate-qa-…@example.invalid` users and randomly generated private passwords.
No emails were sent by these tests; administrative creation was limited to synthetic
QA identities. No real account's verification was bypassed.

1. Account trigger ignores self-assigned metadata role.
2. Real password login and `/auth/v1/user` identity validation.
3. Unverified email rejected.
4. Incorrect password rejected.
5. Trusted verified Operator provisioning.
6. Anonymous internal snapshot RPC access rejected.
7. Authenticated browser-token snapshot access rejected.
8. Account RLS returns only the caller's row.
9. Browser role/membership mutation rejected.
10. Browser Operator provisioning RPC rejected.
11. Traveller supplier-approval attempt rejected.
12. Reviewed supplier onboarding changes the role atomically.
13. Existing Operations intake, confirmation, dispatch and response review persist in cloud.
14. A second real Traveller cannot read another account's case.
15. Operator release, private inbox, closure and replay-safe delivery.
16. A stale database revision leaves no partial write.

The dashboard also confirmed RLS=true for accounts and all six private business tables.

## Browser checks

The local public website and actual password sign-in were inspected in Chrome.
A synthetic Traveller completed the request summary -> confirmation -> processing ->
checked response -> closed case flow, with delivery and closure visible in the timeline.
The verified Supplier reached its separate offer submission workspace; the verified
Operator reached its internal queue and reviewed supplier-application view. Screenshots
were inspected for the public website and all three roles. Synthetic case evidence remains clearly identified as QA data.

## Limits

The owner confirmed self-registration and email verification; Operator provisioning
then succeeded. End-to-end password recovery with the owner's inbox and email delivery
to other addresses have not been tested. Public hosting, production load,
shared supplier organizations and specialist itinerary generation are outside these
checks. See `PORTAL_HANDOFF.md` for implementation boundaries.

The owner-authorised account completed owner-controlled registration and verification,
then received Operator access via the audited trusted
RPC. The five synthetic QA accounts remain active at the owner's explicit request;
no account ban or deletion was performed. Their temporary local credentials remain
in an owner-readable file outside the repository and are not published.

The public website was checked at a 390px viewport: document width equals the viewport
width, with no horizontal overflow. The browser viewport override was reset afterwards.
Jira WN5620-31 through WN5620-38 were verified in Backlog with To Do status, jiaheng guo
as assignee and no sprint assignment; each has an English User Story and acceptance criteria.
