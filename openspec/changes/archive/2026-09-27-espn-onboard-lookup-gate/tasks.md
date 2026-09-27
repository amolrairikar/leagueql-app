## 1. Landing-page gating

- [x] 1.1 In `frontend/src/features/landing_page/landing-page.tsx`, add `needsEspnCredentials`
  state (default `false`) next to the other form state.
- [x] 1.2 Gate the ESPN credential block (SWID/espn_s2 + auto-refresh checkbox) on
  `platform === 'ESPN' && needsEspnCredentials` instead of `platform === 'ESPN'`.
- [x] 1.3 Reset `needsEspnCredentials` (and clear `error`) when the League ID input changes and
  when the platform `<Select>` changes, so a new ID re-runs the lookup gate.

## 2. Connect submit flow

- [x] 2.1 In the ESPN `404` branch of `handleConnectSubmit`: if `needsEspnCredentials` is still
  `false`, set it `true` (revealing the fields) and return without sending `POST /leagues`.
- [x] 2.2 If the fields are revealed but SWID/espn_s2 are empty, keep the existing inline error
  ("Enter your SWID and espn_s2…") and send no `POST /leagues`.
- [x] 2.3 Leave the onboard-in-place path (season derive → `onboardLeague` → poll → clear cookies
  → navigate) unchanged for the revealed-with-credentials case, and leave the `200` route-in path
  unchanged.
- [x] 2.4 Update the ESPN `403` message to: "League already onboarded. Please reach out to your
  leaguemate who onboarded the league to get your league-specific invite link."

## 3. Tests

- [x] 3.1 Update `frontend/src/features/landing_page/__tests__/landing-connect.feature`:
  add a scenario that ESPN selection alone shows no SWID/espn_s2 inputs; add a scenario that a
  first Connect on a `404` reveals the inputs and sends no `POST /leagues`; update the
  onboard-in-place scenario to the two-click flow; update the empty-credentials scenario to a
  second Connect after reveal; update the `403` scenario to the new copy.
- [x] 3.2 Update `landing-connect.steps.test.tsx`: adjust `statefulGetLeague` to return `404`
  for both pre-onboard lookups then `200`; update `connectEspnLeague` to click Connect, fill
  cookies, click Connect again; add the new step definitions; update the `403` assertion copy.
- [x] 3.3 Run `npx vitest run src/features/landing_page/__tests__/landing-connect.steps.test.tsx`.

## 4. Lint, spec sync, verification

- [x] 4.1 From `frontend/`, run `npm run format:fix` and `npm run lint`.
- [x] 4.2 Run `openspec validate --all` and confirm it passes.
- [x] 4.3 `/opsx:archive` to merge the delta into `openspec/specs/frontend/landing-page/spec.md`.
