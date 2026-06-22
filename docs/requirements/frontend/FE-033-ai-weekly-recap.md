# FE-033: AI Weekly Recap

## Description
A premium section on the `/matchups` page that renders the LLM-generated "commissioner's
column" ([BE-022](../backend/BE-022-ai-weekly-recap.md)) for the currently-selected
season/week — a headline plus a narrative body recapping that week's storylines, upsets, and
awards. It is **not** a standalone page or nav entry; it reuses the matchups page's existing
`selectedSeason` / `selectedWeek` state and renders directly **below** the FE-032 weekly awards
& superlatives section (page order: matchups grid → FE-032 superlatives → FE-033 recap).

The recap content is generated server-side and stored as a `RECAP#{season}#WEEK#{WW}` view; the
frontend just fetches and displays the single item for the selected week via the existing BE-005
query client. It mirrors the [FE-032](FE-032-weekly-awards-superlatives.md) pattern: a
premium-gated display of a fetched view, using the shared `toResult` + `<ErrorAlert>` inline
error pattern (no global error store).

## Scope
- Lives on `/matchups` ([FE-006](FE-006-matchups.md)), below the weekly-awards block, scoped to
  the page's season + week navigation. No new route, no sidebar entry.
- Feature folder `src/features/ai_recap/`: `api-calls.ts` (fetch the single
  `RECAP#{season}#WEEK#{WW}` item) and `ai-recap.tsx` (component taking
  `leagueId` / `platform` / `season` / `selectedWeek`, mirroring `<WeeklyAwards>`).
- **Premium-gated:** wrapped in `SubscriptionGuard` on the shared `premium_feature` flag, with
  the section header gated on `isBillingEnabled` so it disappears with the section when `billing`
  is off — identical to how the FE-032 superlatives section is gated.
- **Advertised on the landing/pricing page** ([FE-001](FE-001-landing-page.md)): an "AI weekly
  recap" entry is added to `PREMIUM_FEATURES` so the marketing surface matches what a
  subscription unlocks.

## Edge Cases
- **No recap yet for the selected week** (backfill still running, or a week with no matchups):
  the `RECAP` query returns 404 → render an empty-state message ("No recap for this week yet"),
  not an error.
- **Load failure (5xx) / other error:** surface an inline `<ErrorAlert>`; never throw.
- **Locked (expired/absent subscription with `premium_feature` + `billing` on):** the guard
  renders the blurred lock overlay and the component is **not mounted**, so no `RECAP` fetch
  happens while locked.
- **`billing` off:** the whole section (header + content) is hidden.
- **`billing` on, `premium_feature` off:** the guard is a pass-through and the recap renders for
  everyone.
- **Changing season/week:** refetches the recap for the newly-selected week.

## Acceptance Criteria
- [ ] On `/matchups`, an AI weekly recap section renders below the weekly-awards section,
      showing the headline + narrative body for the selected season/week.
- [ ] Navigating to a different week (or season) refetches and renders that week's recap.
- [ ] A week with no stored recap (404) shows an empty-state message, not an error.
- [ ] A load failure renders an inline error and does not crash the page.
- [ ] With `premium_feature` (and `billing`) on and the subscription expired/absent, the section
      shows the blurred lock overlay and does **not** fetch the recap. With `billing` off the
      section and header are hidden; with `billing` on but `premium_feature` off it renders for
      everyone.

## Sources
`src/features/ai_recap/`, `src/features/matchups/matchups.tsx`,
`src/features/weekly_awards/weekly-awards.tsx` (display pattern),
`src/features/subscription/subscription-guard.tsx`,
`src/features/landing_page/constants.ts` (`PREMIUM_FEATURES`).
