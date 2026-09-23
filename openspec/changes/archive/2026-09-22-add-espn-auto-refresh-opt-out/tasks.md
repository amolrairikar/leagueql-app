## 1. Opt-out confirmation dialog (frontend/navigation-sidebar)

- [x] 1.1 Add `frontend/src/features/sidebar/disable-auto-refresh-dialog.tsx`, a `DisableAutoRefreshDialog({ open, onOpenChange })` following the `TransferOwnershipDialog` pattern (Dialog primitives + `useState` loading/error). Read `getLeagueCookies()` for `leagueId`/`platform`. On confirm, call `setAutoRefresh(leagueId, platform, false)` from `features/connect_league/api-calls.ts`; on success `clearApiCache()` (`@/lib/api-client`) then `window.location.reload()` so `useIsOwner` re-reads `auto_refresh_enabled`; on error surface an inline message (`ErrorAlert` from `@/lib/error-alert`) and keep the dialog open. Copy warns the league stops auto-refreshing and the stored ESPN login may be removed (re-enter cookies to re-enable). Buttons: "Turn Off Auto-Refresh" + "Cancel".

## 2. Sidebar action (frontend/navigation-sidebar)

- [x] 2.1 In `frontend/src/features/sidebar/app-sidebar.tsx`, add `disableAutoRefreshOpen` state and render `<DisableAutoRefreshDialog>` with the other dialogs. Inside the `isOwner` block, next to the Refresh League item, add a `SidebarMenuItem` shown when `currentPlatform === 'ESPN' && autoRefreshEnabled` (destructure `autoRefreshEnabled` from `useIsOwner()`), labeled "Turn Off Auto-Refresh" with a lucide icon, opening the dialog.

## 3. User docs & changelog (frontend/instructions-docs)

- [x] 3.1 In `frontend/src/features/instructions/instructions-page.tsx`: add `<li>Turn Off Auto-Refresh (ESPN only)</li>` to the owner-actions list; fix the ESPN "Automatic Weekly Refresh (opt-in)" paragraph to describe turning it off via the sidebar Turn Off Auto-Refresh action (drop "or use the Auto-Refresh toggle in the sidebar"); correct the Yahoo section to state opt-in is at connect time (drop the false "Auto-Refresh toggle in the sidebar" claim).
- [x] 3.2 In `frontend/src/features/changelog/constants.ts` version `1.8.0`: reword the "Added" item (drop "or with the new Auto-Refresh toggle in the sidebar"; note ESPN owners can turn it off from the sidebar) and the "Changed" item (Yahoo opt-in is at connect time, not a sidebar toggle).

## 4. Tests (frontend component)

- [x] 4.1 `sidebar/__tests__/ownership-gating.{feature,steps.test.tsx}`: add scenarios — ESPN owner with `auto_refresh_enabled: true` sees "Turn Off Auto-Refresh" (and not "Refresh League"); ESPN owner without it does not see "Turn Off Auto-Refresh"; Sleeper/Yahoo owner does not see it.
- [x] 4.2 New `sidebar/__tests__/disable-auto-refresh.{feature,steps.test.tsx}`: confirm sends `PUT /leagues/{id}/auto-refresh` with `{ enabled: false }` (inline `http.put` capturing the body; mock `window.location.reload`); cancel sends no request; an error response surfaces an inline error and keeps the dialog open.
- [x] 4.3 `landing_page/__tests__/static-pages.{feature,steps.test.tsx}`: assert the docs page shows "Turn Off Auto-Refresh (ESPN only)".

## 5. Validation

- [x] 5.1 Frontend (`frontend/`): `npm run format:fix && npm run lint`; `npx vitest run src/features/sidebar src/features/landing_page`. Verify green.
- [x] 5.2 `openspec validate add-espn-auto-refresh-opt-out --strict` passes; then archive after implementation is complete.
