## 1. Route an already-onboarded Yahoo return to the league

- [x] 1.1 In `frontend/src/features/connect_league/api-calls.ts`, widen `onboardYahooLeague`'s
      return type so `data` may be `null` (an already-onboarded league returns `200` with
      `data: null`); leave the shared `OnboardResponse` used by `onboardLeague` unchanged.
- [x] 1.2 In `frontend/src/features/connect_league/yahoo-connect-return.tsx`, guard the
      `pollForCompletion` call on `result.data` being present; when it's null, skip polling and
      fall through to the existing `clearApiCache` → `getLeague` → `setLeagueCookies` →
      `navigate('/home')` route so the user lands on their existing league.

## 2. Tests

- [x] 2.1 Add a scenario to
      `frontend/src/features/connect_league/__tests__/yahoo-connect.feature` for an
      already-onboarded league landing on the dashboard.
- [x] 2.2 Add the matching step + MSW handler (onboard returns `200 {detail, data: null}`) to
      `frontend/src/features/connect_league/__tests__/yahoo-connect.steps.test.tsx`, reusing
      `getLeagueOk` and `renderReturn`.

## 3. Validation

- [x] 3.1 From `frontend/`, run
      `npx vitest run src/features/connect_league/__tests__/yahoo-connect.steps.test.tsx`,
      `npm run lint`, and `npm run format:check`; then
      `openspec validate fix-yahoo-already-onboarded-return --strict`. Verify all pass.
