## Why

Connecting an ESPN league is a two-step detour: typing a League ID on the landing page and
hitting Connect redirects the user to a separate `/connect_league` form, where they must enter
SWID, espn_s2, and manually type the "latest season" as a 4-digit year. Sleeper leagues, by
contrast, onboard in place on the landing page. This makes ESPN — the platform with the most
friction (private cookies) — feel the clunkiest, and the manual season field is an avoidable
source of user error.

## What Changes

- ESPN leagues onboard **in place on the landing page**: selecting ESPN reveals SWID + espn_s2
  boxes next to the League ID box, and a not-yet-onboarded league (`getLeague` → `404`) is
  onboarded without redirecting to `/connect_league`. The Chrome-extension autofill helper (or
  the "get the extension" promo) and the manual "how to pull these from your ESPN cookies"
  instructions render **below the boxes**. An ESPN auto-refresh opt-in checkbox is offered
  inline, matching the existing Yahoo inline flow.
- The ESPN **season is derived automatically**, fetched from the Sleeper NFL-state endpoint
  (`https://api.sleeper.app/v1/state/nfl` → `season`), with a clock-based fallback if the fetch
  fails. The manual "Latest Season" input is **removed** from the UI everywhere.
- Refreshing an existing ESPN league now happens through an **in-dashboard dialog** opened by
  the sidebar "Refresh League" action, instead of navigating to the separate `/connect_league`
  form. The dialog collects SWID/espn_s2 (extension autofill or manual entry with the same
  tooltips), derives the season automatically, refreshes in place, and surfaces the benign
  `429`/`409` cooldown responses. The `/connect_league` form still exists (Yahoo OAuth return,
  direct navigation) and is likewise updated to auto-derive the season with its manual season
  field removed.
- The landing-page ESPN `403` (private, non-member) invite-link path is unchanged.
- No backend change: `POST /leagues` still requires and accepts `season`; it is now sourced
  automatically rather than typed.

## Capabilities

### New Capabilities
<!-- None -->

### Modified Capabilities
- `frontend/landing-page`: the inline-connect existence-check routing now onboards a
  not-yet-onboarded ESPN league in place (inline SWID/espn_s2 + extension helper) instead of
  routing to `/connect_league`.
- `frontend/connect-league`: ESPN onboarding begins inline on the landing page; the ESPN season
  is derived automatically (Sleeper NFL-state fetch with clock fallback) rather than entered,
  removing the manual season field and its live 4-digit validation requirement.
- `frontend/navigation-sidebar`: the "Refresh League" action opens an in-dashboard dialog that
  collects SWID/espn_s2 and refreshes in place (auto-derived season), instead of navigating to
  the `/connect_league` form.

## Impact

- Frontend: `frontend/src/features/landing_page/landing-page.tsx`,
  `frontend/src/features/connect_league/league-connect.tsx`,
  `frontend/src/features/connect_league/league-connect-schema.ts`,
  `frontend/src/lib/season.ts` (new `currentFantasySeason` export + `getCurrentNflSeason`),
  `frontend/src/features/sidebar/use-season-staleness.ts` (import the shared helper), plus a new
  shared `EspnCredentialFields` component.
- New external dependency at runtime: a direct browser `fetch` to `https://api.sleeper.app/v1/state/nfl`
  (mirrors the existing direct Sleeper call in `migrate_league/api-calls.ts`).
- Tests: frontend component tests for `landing_page` and `connect_league` (`__tests__`), with an
  MSW handler for the Sleeper NFL-state endpoint.
- No backend, API-contract, DynamoDB, extension, or infrastructure changes.
