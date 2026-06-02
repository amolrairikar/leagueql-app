# BE-001: League Onboarding

## Description
Onboards a new ESPN or Sleeper fantasy football league into LeagueQL for the first
time. Triggered by `POST /leagues?requestType=ONBOARD`, which validates the request,
creates a `JOB_STATUS` tracking item, and asynchronously invokes the onboarder Lambda.
The onboarder fetches all historical season data from the platform API, uploads the raw
payloads to S3, and hands off to the data processing pipeline ([BE-004](BE-004-data-processing-pipeline.md))
which transforms the data and writes precomputed views to DynamoDB.

A successful onboard produces a canonical league ID (UUID) that unifies a league across
seasons and platforms, a `METADATA` item, a `LEAGUE_LOOKUP` item per platform league ID,
and an incremented `LEAGUE_COUNT`.

## Scope
- Endpoint: `POST /leagues?requestType=ONBOARD` (`src/api/routes.py::onboard_league`).
- Onboarder Lambda: `src/onboarder/` (`handler.py`, `onboarding_service.py`,
  `espn_client.py`, `sleeper_client.py`, `writer.py`).
- Request body: `OnboardRequest` (`leagueId`, `platform`, `season` (ESPN only),
  `s2`/`swid` (private ESPN only)).

## Edge Cases
- **League already onboarded:** `ONBOARD` on an existing canonical league returns `200`
  with "League already onboarded" instead of re-running the pipeline.
- **Private ESPN league:** requires `s2` + `swid` cookies; these are passed once for
  onboarding and must never be logged or persisted.
- **ESPN requires `season`:** the most recent active season is mandatory for ESPN; absent
  for Sleeper (resolved via `previous_league_id` chain).
- **Sleeper multi-season chain:** consecutive Sleeper seasons use different league IDs;
  the onboarder resolves the canonical league via the `previous_league_id` chain.
- **Invalid/expired ESPN credentials:** classified as `ESPN_AUTH` failure with a
  user-friendly message; job recorded as `FAILED`.
- **Platform API unreachable / rate limited / partial data:** onboarding fails cleanly;
  `JOB_STATUS` set to `FAILED` with an appropriate `failure_code`.
- **Onboarding fails before `METADATA` is written:** league does not appear onboarded; a
  retry re-runs the full flow (METADATA write is the commit point).
- **Auction vs. snake drafts:** both ESPN and Sleeper auction drafts must be handled
  (`bid_amount`, `nominating_team_id` populated for auction picks).
- **Invalid `leagueId` format:** must match `^\d+$`; otherwise `422`.

## Acceptance Criteria
- [ ] `POST /leagues?requestType=ONBOARD` with a valid, not-yet-onboarded league returns
      `201` with `{ detail, data: { correlation_id } }` and invokes the onboarder Lambda.
- [ ] A duplicate `ONBOARD` for an already-onboarded league returns `200` and does not
      re-trigger the pipeline.
- [ ] ESPN onboards require `season`; private ESPN leagues require `s2` + `swid`.
- [ ] `s2` / `swid` cookie values never appear in logs or persisted DynamoDB/S3 items.
- [ ] On success: a canonical league UUID, `METADATA`, per-platform `LEAGUE_LOOKUP`, and
      all precomputed view items exist; `LEAGUE_COUNT` is incremented by 1.
- [ ] Raw platform API payloads are written to S3 under `raw-api-data/{canonical_league_id}/`.
- [ ] On any failure a `JOB_STATUS` item is written with `status=FAILED` and a
      `failure_code` / `failure_reason` that the frontend can surface.
- [ ] A `JOB_STATUS` item keyed by `correlation_id` is created so the frontend can poll
      [BE-008](BE-008-job-status-tracking.md).

## Sources
`src/api/routes.py`, `src/onboarder/`, `docs/api/openapi_spec.yaml`, `docs/db/dynamodb_spec.md`.
