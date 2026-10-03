# Proposal

## Why

A signed-in user can only get back to a league by re-entering its platform and league ID in
"Connect Your League", even though LeagueQL already knows which leagues they own or have joined.
A "View My Leagues" list on the landing page lets them jump straight into any of their leagues.
There's no way to answer "which leagues am I in?" efficiently today: membership lives only in
METADATA's `members` String Set, which can't be a GSI key.

## What Changes

- New landing-page **View My Leagues** button (signed-in only) next to "Connect Your League" and
  "View Demo". It expands a list of the user's leagues (platform logo, name, season span, last
  updated, "Moved from ESPN" note, "Reconnect ESPN" flag for an owner needing re-auth), with
  loading, empty, and error states. Clicking a row opens the league. The panel and the Connect
  form are mutually exclusive.
- New **membership index**: one `LEAGUE#{canonical}` / `MEMBER#{clerk_user_id}` item per
  (league, user), plus a new sparse **GSI4** keyed on `member_user_id`. Rows are written when a
  user onboards a league (owner), redeems an invite, claims ownership, or opens a Sleeper league.
  Rows are removed with the league on delete. A one-off backfill seeds rows for existing owners and
  members.
- New authenticated endpoint **`GET /me/leagues`** that returns the caller's leagues.
- Opening a Sleeper league (`GET /leagues/{id}`) now best-effort records the caller in the
  membership index, so Sleeper leagues they've opened appear in their list.
- Changelog: new `1.13.0` release entry announcing the feature.
- No **BREAKING** changes. Authorization still reads METADATA `owner_user_id`/`members`. The index
  is used only for listing.

## Capabilities

### New Capabilities
- `backend/user-leagues`: the per-user league membership index (when rows are written and
  removed) and the `GET /me/leagues` listing endpoint.

### Modified Capabilities
- `frontend/landing-page`: adds the signed-in "View My Leagues" button and expandable league list,
  including its states and how opening a league works.

## Impact

- **Backend:** `src/api/routes.py` (new route; Sleeper open in `get_league`; claim-ownership),
  `src/api/helpers.py` (`add_league_member`, membership/listing helpers), `src/onboarder/writer.py`
  (owner row in the onboard transaction), a new backfill script.
- **Infra:** `infrastructure/modules/dynamodb/main.tf` (GSI4 + attribute definitions) and the API
  role's GSI4 permission. The `GET /me/leagues` API Gateway route comes from its OpenAPI entry.
- **Frontend:** `frontend/src/features/landing_page/` (button + new `my-leagues.tsx` panel),
  `frontend/src/components/api/leagues.ts` (`getMyLeagues`), and
  `frontend/src/features/changelog/constants.ts` (v1.13.0).
- **Docs:** `docs/db/dynamodb_spec.md` (MEMBER item, GSI4) and `docs/api/openapi_spec.yaml`
  (`/me/leagues`).
- **Deploy order:** infra → backend → backfill → frontend.
