## 1. Implementation

- [x] 1.1 In `frontend/src/features/landing_page/landing-page.tsx`, inside the `platform === 'ESPN' && needsEspnCredentials` block, render the message "League not added to LeagueQL yet. Enter your ESPN cookies below to connect." above the `EspnCredentialFields`; verify by loading the landing page, submitting a first Connect on a not-yet-onboarded ESPN league, and seeing the message appear above the SWID/espn_s2 fields.

## 2. Tests & quality

- [x] 2.1 Update the frontend component tests under `frontend/src/features/landing_page/__tests__/` (feature + steps) so the "reveals the credential fields" scenario also asserts the "League not added to LeagueQL yet" message is shown, and confirm it is absent when ESPN is selected but no lookup has resolved; verify with `npx vitest run src/features/landing_page/__tests__/landing-connect.steps.test.tsx` from `frontend/`.
- [x] 2.2 Run `npm run format:fix` and `npm run lint` from `frontend/` and verify both pass.
