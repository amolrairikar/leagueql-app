# Proposal

## Why

LeagueQL's league data refreshes once a week (Tuesday), and every page today is league-wide or
all-time. A manager has little reason to check in more than once a week. A personal page that
answers "how is *my* season going, and what's ahead this week?" gives a more frequent, personal
reason to open the app. It is built from data and calculations the app already has.

## What Changes

- New **My Team** page at `/my_team`. It has its own sidebar entry directly under Home and above
  Standings. It ships on for everyone, with no feature flag. Home is unchanged.
- **First visit:** a "Which team is yours?" picker listing the current season's teams. The choice
  is saved per user, per league.
- **After claiming:** a "Your week" card for the claimed team:
  - last week's result and margin
  - record, rank and points for
  - playoff odds, and the change since last week
  - season-long lineup efficiency, plus last week's points left on the bench
  - this week's matchup (projected score, win probability, all-time head-to-head, last meeting,
    the opponent's recent form)
  - a weekly-awards summary
  - a "Change team" link
- **"Email me each week" row:** a disabled placeholder marked "COMING SOON!". It does nothing
  in this change; weekly email digests are deferred.
- **New backend endpoints** `GET` / `PUT /leagues/{leagueId}/me` read and save the caller's
  claimed team for a league. The claim is stored as a new per-user item in the league's partition,
  so deleting a league also deletes its claims.

## Capabilities

### New Capabilities
- `frontend/my-team`: the My Team page. Covers the claim picker, the Your week
  card and its metrics, edge states (offseason, Week 1, claimed owner missing from the current
  season), the disabled email placeholder, demo mode, and inline errors.
- `backend/user-league-preferences`: per-user, per-league preferences (the claimed team) behind
  `GET`/`PUT /leagues/{leagueId}/me`. Covers authentication, membership gating, validation, and
  deletion along with the league.

### Modified Capabilities
- `frontend/navigation-sidebar`: adds an always-shown "My Team" entry placed between Home and
  Standings.

## Impact

- **Backend:**
  - `src/api/routes.py` and `src/api/helpers.py`: two new endpoints and helpers.
  - New DynamoDB item type `SK=USER#{clerk_user_id}` under `PK=LEAGUE#{canonical_id}`. No new
    table or index.
  - `docs/api/openapi_spec.yaml` and `docs/db/dynamodb_spec.md`.
- **Frontend:**
  - New `frontend/src/features/my_team/`.
  - Route registered in `frontend/src/app/app.tsx`, sidebar entry added in
    `frontend/src/features/sidebar/app-sidebar.tsx`.
  - Demo-mode stub for `/me` in `frontend/src/lib/demo-api.ts`.
  - The page reuses the existing matchup-preview, playoff-predictor, lineup-efficiency and
    weekly-awards calculations.
- **Infrastructure:** API Gateway's routes are generated from `docs/api/openapi_spec.yaml`
  (`infrastructure/regional/main.tf`). Adding `GET`/`PUT /leagues/{leagueId}/me` there, with the
  JWT authorizer and Lambda integration, deploys the new routes.
- **CORS:** API Gateway (`infrastructure/modules/api-gw/main.tf`) and FastAPI (`src/api/main.py`)
  both omitted `PUT` from their CORS allowed methods, which blocks a browser `PUT`. `PUT` is added
  to both. This also unblocks the existing `PUT /leagues/{leagueId}/auto-refresh` call. The
  backend and infra must deploy before the frontend starts calling `PUT /me`.
