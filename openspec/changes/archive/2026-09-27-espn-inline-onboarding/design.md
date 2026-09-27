## Context

See `proposal.md` — Why. Two connect entrypoints exist today:

- **Landing page** (`frontend/src/features/landing_page/landing-page.tsx`) — a plain-`useState`
  inline connect bar (platform `Select` + League ID `Input` + Connect). It calls `getLeague`;
  Sleeper `404` onboards in place (`onboardLeague` + `pollForCompletion`), ESPN `404` redirects
  to `/connect_league`, ESPN `403` shows invite-link guidance.
- **`/connect_league`** (`frontend/src/features/connect_league/league-connect.tsx`) — a
  react-hook-form + zod form with SWID/espn_s2 inputs, a manual "Latest Season" input, the
  extension autofill/promo, and an auto-refresh opt-in. Still needed as the sidebar "Refresh
  League" entrypoint.

Constraints: the season currently comes from the user; the backend `POST /leagues` contract
already requires `season` and is unchanged. There is a precedent for a direct browser call to
the Sleeper API in `frontend/src/features/migrate_league/api-calls.ts` (`getSleeperUsers`, raw
`fetch`, no auth). The clock-based current-season logic already exists as a private
`currentFantasySeason` in `frontend/src/features/sidebar/use-season-staleness.ts`.

## Goals / Non-Goals

**Goals:**
- ESPN onboards in place on the landing page with inline credentials, matching Sleeper.
- Season is derived automatically for every ESPN onboard/refresh; no season input anywhere.
- Share one credential-UI component between the landing page and `/connect_league`.

**Non-Goals:**
- No backend / API-contract / DynamoDB / extension / infra changes.
- Not moving the refresh flow off `/connect_league`.
- Not changing the ESPN `403` invite-link behavior or the Yahoo/Sleeper paths.

## Decisions

- **Season source: fetch at submit time, not on mount.** `getCurrentNflSeason()` is called
  inside the ESPN onboard/refresh submit path (only when a season is actually needed), avoiding a
  wasted request for Sleeper/Yahoo users and any mount-time race. Alternative (fetch on mount and
  cache) adds state and a race for no benefit here.
- **Fail-open with a clock fallback.** `getCurrentNflSeason()` never throws: on any failure it
  returns `String(currentFantasySeason(new Date()))`. This mirrors the backend's fail-open
  `get_nfl_state` and guarantees onboarding is never blocked by Sleeper availability.
- **Centralize season logic in `frontend/src/lib/season.ts`.** Export `currentFantasySeason`
  (moved from `use-season-staleness.ts`, which then imports it — no behavior change) and add
  `getCurrentNflSeason`. Keeps the one "what season is it" definition in one place.
- **Shared `EspnCredentialFields` controlled component.** A presentational component takes
  `swid`/`espnS2` + change handlers + optional errors + an `onAutofill` callback, and owns the
  tooltips, the `useEspnExtensionReady` autofill button / install promo, and the visible manual
  instructions. The landing page drives it with `useState`; `/connect_league` can drive it via
  react-hook-form `setValue`/`watch`. Avoids duplicating the extension wiring in two places.
- **Contextual (not schema) credential validation on the landing page.** The landing bar stays
  plain `useState`. Credentials are required only on the ESPN `404` (onboard) path; if missing
  there, show the existing inline `error` and skip the request. The `200`/`403` branches ignore
  the credential fields, preserving the member-reopen and invite-link paths.
- **Keep `/connect_league` as-is structurally**, only removing the season field and its zod
  member and auto-deriving the season in `onSubmit`.

## Risks / Trade-offs

- **A member re-opening an already-onboarded private ESPN league sees empty credential inputs**
  → they never submit them: the `200` path opens the dashboard and ignores the fields; only the
  `404` onboard path requires them. No functional impact.
- **Sleeper NFL-state endpoint down or returns an unexpected shape** → the clock fallback keeps
  onboarding working with the correct in-season year; worst case pre-September edge is the same
  behavior the app already relies on for staleness.
- **MSW `onUnhandledRequest: 'error'`** → every test that exercises an ESPN onboard path must
  register a handler for `https://api.sleeper.app/v1/state/nfl`, or it fails. Mitigation: add a
  shared `sleeperNflState` helper in `frontend/src/test/msw/server.ts`.
- **Landing bar horizontal space** → adding two ESPN inputs makes the single-row bar crowded;
  the ESPN block wraps to its own row(s) and stays responsive within `max-w-lg` with no
  horizontal page scroll.
