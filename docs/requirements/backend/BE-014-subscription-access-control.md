# BE-014: Subscription Access Control

## Description
Enforces a per-league subscription on the backend API. Each league's `METADATA` item carries a
`subscription_end_time` (ISO 8601 UTC timestamp). A league's subscription is **active** while
`now < subscription_end_time`; it is **expired** when the timestamp is in the past **or absent**.
Expired leagues are blocked from the data and write endpoints (HTTP `402`), while the metadata
and delete endpoints stay reachable so the frontend can read status and users can remove a
league. State is evaluated live on each request — there is no stored status flag and no
scheduled job. The actual `subscription_end_time` value originates from the billing provider
(Clerk/Stripe) and is written at onboarding (or via a future billing webhook).

## Scope
- Helper: `require_active_subscription(canonical_league_id)` (`src/api/helpers.py`) — reads the
  `METADATA` item via `get_league_metadata` and raises `402 Subscription required` when
  `subscription_end_time` is absent or `<= now` (UTC).
- Write helper: `update_subscription_end_time(canonical_league_id, end_time)`
  (`src/api/helpers.py`) — the target for the future billing webhook/manual update.
- **Gated** endpoints (`src/api/routes.py`): `GET /leagues/{id}/query`,
  `POST /leagues/{id}/migrate`, `POST /leagues/{id}/espn_members`, and `POST /leagues`
  **only on the REFRESH path for an already-onboarded league**.
- **Ungated** endpoints: `GET /leagues/{id}` (must stay readable), `DELETE /leagues/{id}`,
  `GET /jobs/{id}`, and new-league `ONBOARD` (no league exists yet to check).

## Edge Cases
- **`subscription_end_time` absent:** treated as expired → `402`.
- **Timestamp exactly equal to now:** treated as expired (`<= now` blocks).
- **New onboarding:** allowed regardless (the league/subscription does not exist yet); the
  onboarder writes `subscription_end_time` when the request supplies it ([BE-001](BE-001-league-onboarding.md)).
- **Reading status while expired:** `GET /leagues/{id}` is never gated, so the frontend can
  always read `subscription_end_time` to render its paywall ([FE-021](../frontend/FE-021-subscription-access-control.md)).
- **Delete while expired:** allowed, so users can clean up lapsed leagues.
- **Existing leagues (no value):** without a backfill they read as expired; a one-off backfill
  of `subscription_end_time` is required before/with deploy.

## Acceptance Criteria
- [ ] A league with `subscription_end_time` in the future reaches gated endpoints (`200`/`202`).
- [ ] A league with a past or absent `subscription_end_time` receives `402` from gated endpoints.
- [ ] `GET /leagues/{id}` and `DELETE /leagues/{id}` succeed regardless of subscription state.
- [ ] New-league `ONBOARD` is never blocked by the gate.
- [ ] REFRESH of an already-onboarded, expired league returns `402`.
- [ ] No scheduled job, EventBridge rule, or extra Lambda is introduced.

## Sources
`src/api/helpers.py` (`require_active_subscription`, `update_subscription_end_time`),
`src/api/routes.py`, `docs/db/dynamodb_spec.md` (METADATA `subscription_end_time`),
`docs/api/openapi_spec.yaml`.
