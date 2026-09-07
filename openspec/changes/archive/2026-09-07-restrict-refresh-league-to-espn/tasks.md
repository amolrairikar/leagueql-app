## 1. Frontend — sidebar gating

- [x] 1.1 In `frontend/src/features/sidebar/app-sidebar.tsx`, wrap the owner-only "Refresh League" `SidebarMenuItem` in `{currentPlatform === 'ESPN' && (...)}`, matching the existing "Invite Leaguemates" gating. Verify via the tests in 3.

## 2. Docs

- [x] 2.1 In `frontend/src/features/instructions/instructions-page.tsx`, change the "League Ownership" owner-actions list entry from `Refresh League` to `Refresh League (ESPN only)`.

## 3. Tests

- [x] 3.1 Update `frontend/src/features/sidebar/__tests__/ownership-gating.*`: the owner scenario used a Sleeper league and asserts "Refresh League" — switch its league to ESPN so the assertion stays valid, and add a scenario that a Sleeper owner does **not** see "Refresh League" (but still sees Delete/Transfer). Verify `npx vitest run src/features/sidebar/__tests__/ownership-gating.steps.test.tsx` passes.

## 4. Quality gates

- [x] 4.1 Frontend lint/format (from `frontend/`): `npm run format:fix` and `npm run lint`.
- [x] 4.2 Run the sidebar suite: `npx vitest run src/features/sidebar`.
- [x] 4.3 `openspec validate --all` passes.
