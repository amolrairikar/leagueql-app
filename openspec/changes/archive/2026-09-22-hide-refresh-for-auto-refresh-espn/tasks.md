## 1. Surface the auto-refresh flag from the ownership hook (frontend/navigation-sidebar)

- [x] 1.1 In `frontend/src/features/ownership/use-is-owner.ts`, add `autoRefreshEnabled: boolean` to `OwnershipState`; set it from `res.data.auto_refresh_enabled === true` alongside `isOwner`, and default it to `false` in the bypass state (demo / no league) and the `.catch`. Reuses the existing `getLeague` fetch — no new request.

## 2. Gate the sidebar Refresh League action (frontend/navigation-sidebar)

- [x] 2.1 In `frontend/src/features/sidebar/app-sidebar.tsx`, destructure `autoRefreshEnabled` from `useIsOwner()` and change the Refresh League gate to `currentPlatform === 'ESPN' && !autoRefreshEnabled`; update the adjacent comment. Verify with jest-cucumber scenarios: an ESPN owner with `auto_refresh_enabled: true` does not see Refresh League, while the existing ESPN-owner scenario (flag absent/false) still does.

## 3. Suppress the reminder banner (frontend/refresh-reminder-banner)

- [x] 3.1 In `frontend/src/features/sidebar/refresh-reminder-banner.tsx`, destructure `autoRefreshEnabled` from `useIsOwner()` and add it to the early-return so an auto-refresh-enabled ESPN league renders no banner; update the doc comment. Verify with a jest-cucumber scenario: a stale, owned ESPN league with `auto_refresh_enabled: true` shows no reminder.

## 4. Validation

- [x] 4.1 Frontend (`frontend/`): `npm run format:fix && npm run lint`; `npx vitest run src/features/sidebar/__tests__/ownership-gating.steps.test.tsx src/features/sidebar/__tests__/refresh-reminder-banner.steps.test.tsx`. Verify green.
- [x] 4.2 `openspec validate hide-refresh-for-auto-refresh-espn --strict` passes; then archive after implementation is complete.
