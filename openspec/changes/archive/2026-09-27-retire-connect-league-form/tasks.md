## 1. Add auto-refresh opt-in to the Refresh League dialog

- [x] 1.1 In `frontend/src/features/sidebar/refresh-league-dialog.tsx`, add an `autoRefresh` `useState` (default false) and render an "enable automatic weekly refresh" checkbox with the explanatory tooltip below the credential fields; send `autoRefresh` from that state in the `POST /leagues` body instead of the hardcoded `false`. Verify via section 4 tests.

## 2. Repoint "View another league" buttons

- [x] 2.1 In `frontend/src/features/ownership/membership-guard.tsx` and `frontend/src/features/connect_league/join-invite-page.tsx`, change the "View another league" button navigation from `/connect_league` to `/?connect=true`. Verify `npm run build:ci` and existing tests pass.

## 3. Remove the ESPN/Sleeper form

- [x] 3.1 Reduce `frontend/src/features/connect_league/league-connect.tsx` to a dispatcher: render `YahooConnectReturn` for `platform=YAHOO`, otherwise `<Navigate to="/?connect=true" replace />`; delete `LeagueConnectForm` and its now-unused imports. Verify `npm run build:ci` typechecks.
- [x] 3.2 Delete `frontend/src/features/connect_league/league-connect-schema.ts` (only the form used it); confirm no remaining importers via `npm run build:ci`.
- [x] 3.3 Delete `frontend/src/features/connect_league/__tests__/connect-league.feature` and `connect-league.steps.test.tsx` (they tested the retired form). Verify the connect_league and yahoo/join-invite tests still pass.

## 4. Tests

- [x] 4.1 Extend `frontend/src/features/sidebar/__tests__/refresh-league.{feature,steps.test.tsx}`: a scenario where checking the opt-in sends `autoRefresh: true` in the refresh `POST /leagues` body, and confirm the default (unchecked) sends a falsy opt-in. Verify `npx vitest run src/features/sidebar/__tests__/refresh-league.steps.test.tsx`.
- [x] 4.2 Run the full suite (`npm run test`) and confirm the removed form tests don't leave dangling references and everything passes.

## 5. Docs, lint, and verification

- [x] 5.1 Update `frontend/src/features/instructions/instructions-page.tsx` auto-refresh opt-in wording so it says the opt-in is on the landing-page onboard and the Refresh League dialog (not a separate connection page).
- [x] 5.2 From `frontend/`, run `npm run format:fix`, `npm run lint`, and `npm run test`; confirm all pass.
- [x] 5.3 Run `openspec validate --all` and confirm it passes.
