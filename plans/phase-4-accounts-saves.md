# Phase 4 — Accounts, Saves, Entitlement Hooks (`apps/accounts`)

Goal: optional accounts on top of the anonymous flow; billing deferred but the
hooks land now so Stripe later is plumbing, not redesign.

## Tasks
- [ ] Register/login/logout (django.contrib.auth, session cookies; no JWT)
- [ ] Claim flow: anonymous session results/profile → user account on signup
      (no data loss mid-flow)
- [ ] History page: past analyses; saved political profile reused across runs
- [ ] Shareable result links (public read-only)
- [ ] `plan_tier` on user + `Entitlements` interface: analyses/month, max
      candidates, freshness override
- [ ] Enforcement at job creation; limits surfaced in UI (no payments yet)
- [ ] Rate limiting per IP/session for anonymous abuse control
- [ ] Tests: claim flow, entitlement math, anonymous limits

## Exit criteria
- [ ] Anonymous user signs up mid-flow without losing their results
- [ ] Entitlements enforced + documented; Stripe-ready
