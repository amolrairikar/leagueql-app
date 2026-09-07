## 1. Frontend — season-staleness hook

- [x] 1.1 Add `useSeasonStaleness()` at `frontend/src/features/sidebar/use-season-staleness.ts`, returning `{ isStaleSeason: boolean }`. Read `seasons`/`leagueId` from `getLeagueCookies()`; bypass (always `false`) in demo mode or when no league. Compute the current fantasy season on mount (inside `useEffect`, keeping render pure) as `now.getMonth() >= 8 ? now.getFullYear() : now.getFullYear() - 1`; set `isStaleSeason = seasons.length > 0 && max(seasons as numbers) < currentSeason`. Verify via the banner test below.

## 2. Frontend — banner

- [x] 2.1 Create `frontend/src/features/sidebar/sleeper-stale-season-banner.tsx`: bail (`return null`) in demo mode, no league, or `platform !== 'SLEEPER'`; use `useIsOwner()` + `useSeasonStaleness()`; render nothing while ownership loads, if not owner, or if not stale; otherwise render the thin `h-8` bar (same shell as `refresh-reminder-banner.tsx`, no dismiss button) with the message `Not seeing your current season's data? Enter your latest season's league ID on the landing page.` and "landing page" as a `<Link to="/">`. Verify via 2.3.
- [x] 2.2 Render `<SleeperStaleSeasonBanner />` in `AppLayout` (`frontend/src/app/app.tsx`) directly below `<RefreshReminderBanner />`. Verify the app builds and the banner appears on main-app routes for a stale Sleeper league.
- [x] 2.3 Add a jest-cucumber pair under `frontend/src/features/sidebar/__tests__/` (`sleeper-stale-season-banner.feature` + `.steps.test.tsx`) with MSW-mocked `getLeague` (`leagueMetadata`) and `vi.setSystemTime` to pin the date, covering: Sleeper+owner+behind → shown; Sleeper+owner+current → hidden; Sept-cutover (Aug prior-year → hidden, Sept current-year → shown); non-owner → hidden; ESPN → hidden; demo mode → hidden; no league / empty seasons → hidden. Verify `npx vitest run frontend/src/features/sidebar/__tests__/sleeper-stale-season-banner.steps.test.tsx` passes.

## 3. Quality gates

- [x] 3.1 Frontend lint/format (from `frontend/`): `npm run format:fix` and `npm run lint`.
- [x] 3.2 Run the frontend suite: `npx vitest run src/features/sidebar` (both banner suites green).
- [x] 3.3 `openspec validate --all` passes.
