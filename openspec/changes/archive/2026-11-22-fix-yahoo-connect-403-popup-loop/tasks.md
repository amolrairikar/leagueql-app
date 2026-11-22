# Tasks

## 1. Classify the 403 and bound consent

- [x] 1.1 In `frontend/src/features/landing_page/use-landing-page.tsx`, split `handleYahooConnect` so `POST /leagues` and `GET /leagues/{id}` have separate error handling: a `403` from `getLeague` sets the not-a-member invite-link message, stops loading, and never calls `startYahooOauth`; a non-`403` `getLeague` failure sets the generic error. Verify with `npx vitest run src/features/landing_page` (new scenarios in 2.1) and by reading that no `getLeague` error path reaches `startYahooOauth`
- [x] 1.2 Add an `afterConsent` argument (default `false`) to `handleYahooConnect`; pass `true` from the popup `postMessage` handler and the return-resume effect; when `true`, a "link first" `403` or `YAHOO_AUTH` failure sets "Yahoo linking didn't complete. Please try again.", stops loading, and does not call `startYahooOauth`. Verify with the bounded-retry scenarios in 2.1

## 2. Component tests (same change)

- [x] 2.1 Update `frontend/src/features/landing_page/__tests__/landing-connect.feature` and `landing-connect.steps.test.tsx` (MSW): add scenarios for (a) already-linked caller, `POST /leagues` `200` already onboarded, `GET /leagues/{id}` `403` → invite-link alert and no consent popup/authorize request; (b) `GET /leagues/{id}` `500` → generic error, no popup; (c) consent popup links but the resumed onboard returns `403` "link first" → inline error and exactly one popup opened; (d) rewrite "A revoked Yahoo link surfaced on return reopens the consent popup" to assert the inline retry error and no popup. Verify with `npx vitest run src/features/landing_page` from `frontend/` passing, and that the existing first-attempt consent, blocked-popup, dismissed-popup, and revoked-link-on-first-attempt scenarios still pass
- [x] 2.2 Confirm no other test or spec asserts the old behavior: `grep -rn "reopens the consent popup\|link first" frontend/src` and review each hit; verify migrate-league tests (`npx vitest run src/features/migrate_league`) still pass unchanged

## 3. Quality checks

- [x] 3.1 From `frontend/`, run `npm run format:fix`, `npm run lint`, and `npm run build:ci`; verify all pass with no new warnings
- [x] 3.2 Run `npx @fission-ai/openspec@latest validate --all` and verify the two delta specs (`frontend/connect-yahoo-league`, `frontend/landing-page`) pass

## Workflow follow-up

- Archive with `/opsx:archive` after deploy so the deltas merge into `openspec/specs/frontend/`.
- No backend, OpenAPI, DynamoDB, or architecture-diagram changes; backend tests are unaffected.
- Manual check after deploy: sign in with a non-owner account, connect an already-onboarded Yahoo league, and confirm the invite-link message appears with no popup.
