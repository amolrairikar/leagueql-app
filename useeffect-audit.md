# `useEffect` Re-render Audit — `frontend/`

Reviewed every `useEffect` in `frontend/src` (24 files) for unnecessary effects that
trigger avoidable re-renders. **Overall the codebase is healthy:** most effects are
legitimate (imperative DOM scrolling, event-listener subscriptions, timers, data
fetching, or external-store sync) and several components already use the modern
patterns — `use()` + Suspense for data (`matchups`, `player_records`, `matchup_records`)
and render-phase state reset (`manager-history` `prevYear`). The findings below are the
genuine improvement candidates.

| Finding ID | Location | Criticality | Status | Rationale |
|------------|----------|-------------|--------|-----------|
| UE-01 | `src/hooks/use-mobile.ts` | Medium | ✅ Fixed | `isMobile` was seeded to `undefined` and only set inside the effect on mount, forcing a guaranteed second render for every consumer (sidebar, etc.) on first paint. The width was also computed twice (once in the effect body, once in `onChange`). Now reads the media query synchronously during render via `useSyncExternalStore` — eliminates the mount re-render and the duplicate read. |
| UE-02 | `src/features/playoff_bracket/playoff-bracket.tsx` | Medium | ✅ Fixed | Was the only data component still fetching inside an effect with manual `loading`/`error` state; each `selectedSeason` change fired `setLoading(true)` → fetch → multiple `setState` calls, producing extra render passes. Migrated to the `useMemo(() => fetchPromise)` + `use()`/Suspense pattern used by `matchups`/`player_records`/`matchup_records`: a `BracketContent` child `use()`s a `toResult`-wrapped promise, fetch/derivation moved into a pure `processBracketData` helper, and the duplicated championship-week logic deduped into `championshipWeekFor`. |
| UE-03 | `src/features/landing_page/landing-page.tsx:98` | Low | Ignored (per request) | `setShowConnectForm` is derived from `window.location.search`, which is available synchronously at mount, so it causes an unnecessary post-mount render. It legitimately also depends on the async Clerk `isSignedIn`, so it can't be fully replaced by lazy initial state, but the URL read could be hoisted to `useState(() => …)` and the effect narrowed to only react to `isSignedIn`. |
| UE-04 | `src/features/connect_league/league-connect.tsx`, `src/features/migrate_league/migrate-league.tsx`, `src/features/connect_league/join-league-dialog.tsx` | Low | ✅ Fixed | Identical `onEspnExtensionReady` subscription effect with an `if (extensionReady) return;` guard and `[extensionReady]` dependency tore down and re-subscribed once when the flag flipped. Extracted into a shared `useEspnExtensionReady()` hook (`src/hooks/use-espn-extension-ready.ts`) backed by `useSyncExternalStore`, replacing the three duplicated `useState`+`useEffect` pairs with a single synchronous read. |
| UE-05 | `src/app/app.tsx:54` + `src/components/scroll-to-top.tsx:13` | Low | Ignored (per request) | Two separate null-rendering components each run an effect on `location.pathname` change (route telemetry vs. scroll reset). Both are individually fine; noting only that they could be consolidated into one route-change effect to avoid two mounted listeners doing pathname work. No correctness or measurable perf impact. |

## Reviewed and intentionally NOT flagged

- **scrollIntoView effects** (`matchups:261`, `player_records:226`, `matchup_records:394`,
  `manager_comparison:474`, `manager_history:594`, `playoff_bracket:253`,
  `changelog`, `privacy`, `extension-privacy`, `instructions:281`) — legitimate
  imperative DOM side effects that can't run during render.
- **Event-listener / external-store subscriptions** (`sidebar.tsx:96`,
  `theme-provider.tsx:27`, `feature-flags-provider.tsx:23`, `auth-token-bridge.tsx:19/24`)
  — correct use of effects for subscriptions with cleanup.
- **`feature-flags-provider` `version` + `key` remount** — deliberate and documented;
  the synchronous flag reads require a subtree remount to re-evaluate. Correct.
- **Data-fetch effects in guards/hooks** (`membership-guard.tsx:30`,
  `use-subscription.ts:139`, `use-is-owner.ts:31`) — standard fetch-on-mount with
  `cancelled` cleanup; `use-subscription` already explicitly seeds bypass state in
  `useState` to avoid a cascading render.
- **`manager-history.tsx:586` `prevYear` reset** — exemplary render-phase state
  adjustment (no effect); a model the rest of the codebase should follow.
- **Loading-message interval timers** (`landing-page.tsx:112`,
  `league-connect.tsx:171`) — timer side effects that correctly belong in an effect.
