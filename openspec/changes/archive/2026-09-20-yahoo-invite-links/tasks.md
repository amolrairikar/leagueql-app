## 1. Backend

- [x] 1.1 In `src/api/routes.py`, change the `create_invite_token` guard from `platform != Platform.ESPN` to `platform == Platform.SLEEPER`, and update the error `detail` + docstring to gated-platform (ESPN and Yahoo) wording. Verify a Yahoo mint returns a token and a Sleeper mint returns `400`.
- [x] 1.2 In `src/api/routes.py`, make the same guard + copy change in `accept_invite`. Verify a Yahoo redemption adds the caller to `members` and a Sleeper redemption returns `400`.

## 2. Frontend

- [x] 2.1 In `features/sidebar/app-sidebar.tsx`, change the Invite Leaguemates gate from `currentPlatform === 'ESPN'` to `currentPlatform !== 'SLEEPER'`. Verify the action shows for a Yahoo owner and stays hidden for Sleeper.
- [x] 2.2 In `features/connect_league/join-invite-page.tsx`, change the two `platform !== 'ESPN'` checks (invalid-link guard and effect guard) to treat Sleeper/missing platform as invalid and ESPN/Yahoo as valid. Verify a Yahoo `/join` link redeems and a Sleeper link shows the invalid-link error.
- [x] 2.3 In `features/ownership/invite-link-dialog.tsx`, replace the "no ESPN cookies needed" copy with platform-neutral wording (e.g. "…without their own ESPN or Yahoo login"). Verify the dialog renders the neutral copy.
- [x] 2.4 In `features/ownership/membership-guard.tsx`, generalize the ESPN-specific private-league copy and its platform condition so the invite-link backdrop also fires for Yahoo `403`s. Verify a Yahoo non-member sees the invite-link guidance with no cookie form.
- [x] 2.5 Reviewed the non-member `403` guidance in `features/connect_league/league-connect.tsx` and `features/landing_page/landing-page.tsx`: the connect form offers only ESPN/Sleeper (no Yahoo submit path) and the landing page routes Yahoo through `handleYahooConnect` before the ESPN-403 copy, so the ESPN wording sits on genuinely ESPN-only paths. Yahoo's non-member join path is `join-invite-page` + `MembershipGuard` (both generalized). No change needed.

## 3. Specs & docs sync

- [x] 3.1 Update the `openspec/specs/backend/league-authorization/spec.md` Purpose sentence (and `openspec/specs/frontend/connect-league/spec.md` Purpose) to platform-neutral gated-platform wording, since the delta only touches requirements. Verify `openspec validate --all` passes.
- [x] 3.2 Generalize the invite endpoint descriptions in `docs/api/openapi_spec.yaml` (invite-token / accept-invite) from ESPN-only to gated platforms. Verify the spec still parses.
- [x] 3.3 Confirm `docs/db/dynamodb_spec.md` `members` / `invite_token_hash` wording is platform-neutral; adjust if it names ESPN.

## 4. Tests

- [x] 4.1 In `tests/unit/api/test_endpoints.py`, add Yahoo cases to `TestInviteTokenEndpoint` and `TestAcceptInviteEndpoint` (mint stores hash, valid redeem adds member, reusable, wrong token `403`, no token `404`), keeping the Sleeper-`400` cases. Verify `pipenv run pytest tests/unit/api/test_endpoints.py -k "Invite or Accept"` passes.
- [x] 4.2 In `tests/component/features/league_ownership.feature` + `steps/league_ownership_steps.py`, add a Yahoo invite scenario (mint → join → read across the members boundary); keep the Sleeper-rejected scenario. Verify `pipenv run behave tests/component` passes.
- [x] 4.3 Add/extend frontend jest-cucumber pairs — `ownership/__tests__/invite-link.*` (Yahoo mint + neutral copy), `connect_league/__tests__/join-invite.*` (Yahoo redeem, Sleeper invalid), `ownership/__tests__/membership-guard.*` (Yahoo private-league guidance). Verify `npx vitest run src/features/ownership src/features/connect_league` passes.

## 5. Lint, format & validate

- [x] 5.1 Run `pipenv run ruff check --fix . && pipenv run ruff format .` and, from `frontend/`, `npm run lint && npm run format:fix`. Verify both are clean.
- [x] 5.2 Run `openspec validate --all`. Verify it passes with no dangling references.
