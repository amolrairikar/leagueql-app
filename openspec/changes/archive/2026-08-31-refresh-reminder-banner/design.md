## Context

See proposal.md — Why. The frontend has no current-league object or context; consumers read
`{ leagueId, platform }` from `getLeagueCookies()` (localStorage) and fetch server fields via
`getLeague(leagueId, platform)`. `GET /leagues/{id}` today returns only
`{ seasons, league_name, is_owner }`, so the frontend cannot know when a league was last
refreshed. The `METADATA` item already carries `onboarded_at` (required) and `last_refresh_at`
(written only on REFRESH, absent on a never-refreshed league). The refresh cooldown is 7 days
(`REFRESH_COOLDOWN_DAYS = 7`), so ">7 days stale" coincides with "refresh is now permitted".

## Goals / Non-Goals

**Goals:**
- Expose enough on `getLeague` for the frontend to compute data freshness.
- Render an owner-only, ESPN-only reminder that self-clears once the league is refreshed.

**Non-Goals:**
- No new current-league context/provider — reuse the existing per-consumer `getLeague` pattern.
- No feature flag or persisted dismissal (unlike the promotional `informational-banner`).
- No banner for Sleeper (auto-refreshed) or for initial-onboard freshness edge tuning beyond
  the `last_refresh_at ?? onboarded_at` fallback.

## Decisions

- **Freshness = `last_refresh_at ?? onboarded_at`.** `last_refresh_at` is null until the first
  REFRESH, so using it alone would make every never-refreshed league look infinitely stale.
  `onboarded_at` is always present, so it is the correct baseline for a league's data age.
  Alternative (backend computes a single derived `data_as_of`): rejected — exposing the two raw
  timestamps keeps the API honest and the fallback logic visible in one small frontend hook.

- **Owner-only + not dismissible (confirmed with user).** Only owners see the sidebar's
  "Refresh League" button (`useIsOwner`), so the reminder is only actionable for them. It has no
  X button because it auto-hides the moment the data is fresh; a permanent dismissal would
  defeat a recurring reminder.

- **Separate component, not the existing `Banner`.** The promo `Banner`
  (`frontend/src/components/banner.tsx`) is feature-flag-gated and localStorage-dismissible with
  static content — different concerns. A new `RefreshReminderBanner` co-located under
  `frontend/src/features/sidebar/` (it points at the sidebar's action) reuses only the thin
  `h-8` bar styling.

- **Reuse `getLeague` + a small `useLeagueFreshness()` hook** beside `use-is-owner.ts`, returning
  `{ loading, lastUpdated: Date | null }`. The banner reads ownership from the existing
  `useIsOwner()` and freshness from the new hook. Both go through the same `getLeague` path,
  which the api-client dedupes in-flight and caches for 30s, so the extra consumer adds no real
  network round trip.

- **Render in `AppLayout`** (`frontend/src/app/app.tsx`) next to `<Banner />`, so it covers every
  main-app route and is naturally excluded from public marketing routes.

## Risks / Trade-offs

- [A never-refreshed league onboarded >7 days ago shows the banner immediately] → Intended: its
  data really is >7 days old and a refresh is permitted, so the reminder is correct.
- [Two extra `getLeague` consumers on the page] → Mitigated by the api-client's in-flight dedup
  and 30s cache keyed by request path; no additional network cost.
- [Adding fields to the `getLeague` payload] → Additive and nullable; `required` stays `[seasons]`,
  so existing clients are unaffected.
