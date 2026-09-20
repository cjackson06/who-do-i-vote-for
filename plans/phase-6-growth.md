# Phase 6 — Growth Features (independently shippable)

Sequencing flexible; each item ships on its own.

## Onboarding
- [ ] Swipe onboarding: stance-statement bank (curated + LLM-seeded, cached in
      DB), TS island for swipe UX, maps to the same `UserProfile` as the
      questionnaire

## Data sources
- [ ] YouTube transcript adapter (interviews/debates)
- [ ] Voting history adapter (GovTrack / VoteView-class sources)
- [ ] Social media adapter (hardest — platform API constraints)

## Elections
- [ ] Local elections (`apps/elections`): Google Civic Information API /
      Vote411-class sources; zip → ballot → candidates pipeline

## Monetization & ops
- [ ] Stripe billing: checkout, webhooks, entitlement sync (hooks from Phase 4)
- [ ] Hosting selection + deploy (host-agnostic until now; Fly/Railway/Cloud Run
      shortlist)
- [ ] Scale-out: Redis pub/sub for SSE + worker extraction if concurrency demands
- [ ] Internationalization groundwork if expanding beyond US elections
