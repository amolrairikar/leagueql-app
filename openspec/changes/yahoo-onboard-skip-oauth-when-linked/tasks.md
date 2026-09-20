# Tasks

## 1. Rework the landing-page Yahoo connect branch

- [x] 1.1 In `handleConnectSubmit` (`frontend/src/features/landing_page/landing-page.tsx`), replace the unconditional `getYahooAuthorizeUrl` redirect in the `platform === 'YAHOO'` branch with an optimistic in-place onboard: call `onboardYahooLeague(leagueId)` first, keeping the `loading`/progress UI running; verify with the new/updated component tests in task 2.
- [x] 1.2 On a `correlation_id` response, `pollForCompletion`; on success `clearApiCache`, `getLeague`, `setLeagueCookies`, and `navigate('/home')` — mirroring the Sleeper branch. Verify the "already linked — onboard in place" scenario passes.
- [x] 1.3 On a `200` null-`data` response (already onboarded), skip polling and route straight into the league (`getLeague` → `setLeagueCookies` → `/home`). Verify the "already onboarded" scenario passes.
- [x] 1.4 On a `403` from the onboard call, fall back to `getYahooAuthorizeUrl(leagueId)` and full-page redirect to the consent URL. Verify the "not linked — begin consent" scenario passes.
- [x] 1.5 On a poll failure with `failureCode === 'YAHOO_AUTH'`, redirect to the OAuth (re)link via `getYahooAuthorizeUrl`; on any other poll/onboard failure, surface the existing generic inline error. Verify with the revoked-link and generic-failure scenarios.
- [x] 1.6 Ensure `loading` is reset (`setLoading(false)`) on every terminal branch that does NOT full-page-redirect, and left set on the redirect branches (navigation leaves the page). Verify no lingering spinner in the success/error test scenarios.

## 2. Tests

- [x] 2.1 Update `frontend/src/features/landing_page/__tests__/landing-connect.feature` + `.steps.test.tsx`: change the existing "Connecting a Yahoo league starts the OAuth flow" scenario to cover the unlinked (`403` → consent redirect) case, and add scenarios for already-linked (onboard + poll → `/home`), already-onboarded (null data → `/home`), and `YAHOO_AUTH` re-link. Verify with `npx vitest run src/features/landing_page/__tests__/landing-connect.steps.test.tsx` from `frontend/`.
- [x] 2.2 Run the full frontend test suite and lint/format: `npm run test`, `npm run lint`, `npm run format:fix` from `frontend/`. Verify all pass.

## 3. Validate

- [x] 3.1 Run `openspec validate yahoo-onboard-skip-oauth-when-linked --strict` and confirm it passes.
