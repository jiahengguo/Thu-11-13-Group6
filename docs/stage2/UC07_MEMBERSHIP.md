# UC-07 membership and premium access

The membership page now displays a fresh server decision, labelled simulated advertising for Free users, no advertisements for active Paid users, a Paid-only interactive sample route, and member-offer eligibility. Stop buttons support keyboard navigation. The sample route is explicitly not a traveller itinerary or live navigation.

Existing trip checks continue to enforce two simultaneous Planned/Active trips and five inclusive calendar days for Free members, with fresh checks before presentation, adoption and starting. Expired Paid membership falls back to Free rules. Evidence failures return VERIFICATION_FAILED. Replaying a protected-feature request key re-evaluates current authority and records the fresh decision instead of disclosing protected content using cached authority. Membership overview reads evaluate fresh evidence without writing an audit command or changing the shared business revision; map, ad-free and member-offer actions retain their decision audit.

## Provider boundary

Inject a BenefitsProvider-compatible object through Portal/make_server benefits= or OperationsService benefits=. It supplies route(), advertisements(), offers(). SimulatedBenefits is the explicit default. Replace it with a verified adapter for real route/content/rule sources. A configured provider failure must propagate; there is no automatic fallback to simulation. Authenticated membership continues to come from Supabase, not this content provider.

The simulated UC-08 rule is labelled as simulated approved input. Production rule approval must come from the trusted UC-08 source. Clients submit only rule IDs, never approval flags or discount amounts. Persisted rules take precedence over sample IDs. Eligibility records include rule identity, source, version and membership decision; UC-06 owns customer-specific pricing and minimum-margin checks. This change does not implement UC-08 campaign management or automatic discount adoption in UC-01.

## Acceptance boundary

Operations regression and new tests cover map denial, ad separation, Paid/Free offer eligibility, missing rules, provider evidence failure, and expired membership with a replayed request ID. Full release and browser validation must be recorded separately. The route is currently a sample rather than a map of each saved plan. These limits must not be described as completed personalised mapping or end-to-end discounted planning.

## Verified in this branch

Operations regression: 40 tests passed. UC-07 targeted tests: 5 passed, including portal adapter membership changes and request-key replay. JavaScript syntax and git diff whitespace checks passed. Browser visual review and real-provider acceptance have not been performed.

Full regression during implementation: 311 tests passed in 211.504 seconds. After final membership snapshot/rule-validation changes, UC-07 targeted tests (5) and portal tests (30) passed. These counts overlap and must not be added together.
