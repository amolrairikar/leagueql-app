# FE-004: Home Dashboard

## Description
The `/home` landing dashboard for a connected league. Summarizes the league at a glance:
all-time standings (regular season and playoff), a championship timeline per owner, and
headline league stats (total matchups, total members, unique champions). Owner identities
are stabilized across seasons and remapped through platform-migration mappings so a manager
is counted consistently over time.

## Scope
- Route: `/home` (protected, app layout) (`src/app/app.tsx`).
- Component: `src/features/home_page/home-page.tsx`; API in `api-calls.ts`.
- Reads standings, matchups, teams, playoff bracket, and platform-migration views via
  [BE-005](../backend/BE-005-query-precomputed-views-api.md).

## Edge Cases
- **Migrated league:** owner IDs remapped through the `PLATFORM_MIGRATION` mapping; the most
  recent team identity per owner is used for display.
- **Playoff standings:** count only winners'-bracket games.
- **Single season / brand-new league:** all-time tables and timeline must render with one
  season of data.
- **Co-owners:** handled via primary/secondary owner IDs without double counting.
- **Missing logos:** fall back to a generated team avatar / owner-stable color.
- **No champion for a season:** the champions grid distinguishes an in-progress season from a
  completed one. The most recent season with no recorded champion is shown as **"TBD"** (and
  highlighted as pending); any earlier season with no champion is a completed season with no
  recorded title and is shown as **"N/A"** (not highlighted). Neither counts toward the
  unique-champion or championship totals.
- **Empty seasons (expired cookies):** if the `leagueSeasons` cookie expires while `leagueId`
  persists, `seasons` is `[]` and the stats array is empty. The stats grid must not crash when
  the "Seasons played" item is absent — it renders three cards instead of four.
- **Data load fails:** all summary sections derive from a single league-data request; on failure
  the dashboard shows one inline error (an `ErrorAlert`) in place of the stats/champions/standings/
  chart, rather than silently rendering empty tables. There is no global error banner.

## Acceptance Criteria
- [ ] `/home` shows all-time regular-season standings and playoff standings with
      owner-stable identities and colors.
- [ ] A championship timeline reflects winners'-bracket finals wins per owner.
- [ ] Headline stats show total matchups, total members, and unique champions.
- [ ] Owner identities are correct across migrated platforms.
- [ ] The dashboard renders correctly for a one-season league and an in-progress season.
- [ ] A season with no champion shows "TBD" only for the most recent season; a completed
      earlier season with no champion shows "N/A".
- [ ] If the league-data request fails, an inline error is shown in place of the summary sections
      (no global error banner).

## Sources
`src/features/home_page/home-page.tsx`, `src/lib/error-alert.tsx`, `src/lib/result.ts`.
