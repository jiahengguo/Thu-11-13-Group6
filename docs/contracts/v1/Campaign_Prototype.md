# Campaign prototype contract — campaign-1

Owner: Supplier Partnership (Jason). Traces and domain reviews reuse the shared
`TraceEvent`, `SubjectRef` (`CampaignProposal`) and `ReviewResult` definitions.
This contract adds application records without changing the eight existing
language-neutral contracts. Input schemas are defined in
`src/tripmate/supplier/campaigns.py` (`BRIEF`, `COPY_SCHEMA`); undeclared fields fail.

## Confirmed brief

The Operator supplies `objective`, `audience`, `audienceTiers`, `channel`, timezone-aware
`startAt`/`endAt`, AUD-cent string `budget`, positive integer `units`, `restrictions`,
approved `offerIds`, and nullable `memberOffer`. Explicit `confirmed: true` is required.

`memberOffer` contains `eligibleTiers`, fixed AUD-cent string `discount`, `validFrom`
and `validUntil`. Its validity fits the campaign period. Benefit eligibility and
advertising audience are separate: Paid benefit eligibility does not permit Paid ads.

Permitted channels and costs are versioned simulated configuration in `CHANNELS`/
`POLICY`, not ad-platform prices or user-editable arithmetic. The configured restrictions
are No personal targeting, No guaranteed outcomes, No real booking or payment claims.
Unsupported restrictions require an implementation/policy update; they are not silently waived.

## Backend records

- `campaign`: current projection, campaign ID, material version, optimistic `revision`,
  confirmed brief, state, review, decision and `approved` flag.
- `campaign_brief`: immutable confirmed brief for `campaignId/materialVersion`.
- `campaign_proposal`: immutable evaluated content and exact supplier snapshots,
  evidence, deterministic cost items/checks and drafting mode for that version.
- `campaign_decision`: append-only actor, reason, timestamp, review ID and material version.
- `campaign_history`: append-only state/action evidence linked by campaign ID.
- `member_offer`: approved rule ID, campaign/version/approval IDs, eligible tiers,
  applicable offers, fixed AUD reduction and validity. A new campaign version invalidates it.
- `member_quote`: private customer-specific PriceBreakdown and entitlement evidence.
  Reusable base SupplierOffer/PriceBreakdown records are unchanged.

New record kinds use the existing backend-only atomic `tripmate_commit` adapter. No
new public tables, RLS grants or database migration are required by this feature.

## Portal API

All POSTs require the existing authenticated HttpOnly session, CSRF token, same-origin
request and stable `requestKey`. Operator mutations reject client-supplied approval flags,
prices, channel costs, IDs for a different revision, and arbitrary decision fields.

- Operator GET `/api/campaigns`, `/api/campaigns/catalog`,
  `/api/campaigns/view?campaignId=…`.
- Operator POST `/api/campaigns/save`: requestKey, nullable campaignId, revision,
  brief, confirmed. A change creates a new material version and clears prior authority.
- Operator POST `/api/campaigns/evaluate`: requestKey, campaignId, revision.
- Operator POST `/api/campaigns/decide`: requestKey, campaignId, revision,
  decision (APPROVE / REQUEST_REVISION / REJECT), reason.
- Traveller GET `/api/campaigns/benefits`: currently eligible neutral member benefits;
  no campaign advertising copy, supplier cost or margin is returned.
- Traveller POST `/api/campaigns/quote`: requestKey, memberOfferRuleId, offerId.
  Exactly one rule is accepted. UC-07 eligibility and UC-06 final margin are rechecked.
  `quotation` is a public projection, not the full private PriceBreakdown contract.
- `/api/operations/intake` accepts campaignId, channel SIMULATED_CAMPAIGN and explicit
  consent. The backend rechecks current campaign authority, active dates and eligible
  Free membership. Intake/lead evidence retains the campaign ID, material version and
  source channel; confirmation and external responses remain Operations responsibilities.

## State and authority

Confirmed save -> DRAFT. Successful model drafting/checks/review -> AWAITING_APPROVAL.
Human decision -> APPROVED, REVISION_REQUIRED or REJECTED. Missing/failed drafting or
checks -> REVISION_REQUIRED with a reason; no inferred approval. Save failure is atomic.
Revision creates a new DRAFT version, preserving earlier proposal/decision evidence.

Approval and quote/use checks compare exact current supplier versions, fingerprints,
validity, price policy, ownership/case withdrawal and restricted approval authority.
Reopening a stale approved campaign invalidates its current authority and member rule.
No scheduler or external advertising, booking, payment or publication action is implemented.
