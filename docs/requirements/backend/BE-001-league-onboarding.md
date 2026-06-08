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
- **Sleeper chain terminator (`"0"` vs `null`):** the chain walk stops at the founding
  season, which Sleeper marks either with the string `previous_league_id == "0"` (leagues
  created as a continuation) **or** with JSON `null` (Python `None`, for leagues created
  fresh). Both — and any other falsy value — terminate the walk; the onboarder must never
  follow a `null` into a fetch for league `None` (which 404s and fails onboarding).
- **Not-yet-started Sleeper season:** a renewed Sleeper season that has not begun (league
  `status` of `pre_draft` or `drafting`) carries no usable data — empty rosters, empty
  matchups, no draft picks. The onboarder excludes such seasons from the resolved season
  list (`SleeperClient._get_league_seasons`) so they never reach S3, the processor, or any
  precomputed view; only seasons with `status` of `in_season` or `complete` are kept. As a
  result the not-yet-started season never appears in any dropdown, chart, or calculation,
  and is picked up automatically once it flips to `in_season`. Onboarding a Sleeper league
  whose **only** season is not-yet-started fails with a friendly `NOT_STARTED` message
  rather than writing empty records.
- **Invalid/expired ESPN credentials:** classified as `ESPN_AUTH` failure with a
  user-friendly message; job recorded as `FAILED`.
- **Platform API unreachable / rate limited / partial data:** onboarding fails cleanly;
  `JOB_STATUS` set to `FAILED` with an appropriate `failure_code`.
- **Onboarding fails before `METADATA` is written:** league does not appear onboarded; a
  retry re-runs the full flow (METADATA write is the commit point).
- **Onboarder async invocation exhausts retries:** the onboarder is invoked
  fire-and-forget (`InvocationType="Event"`) by the API ([BE-002](BE-002-league-refresh.md),
  [BE-003](BE-003-league-migration.md)) and the scheduled refresh
  ([BE-012](BE-012-scheduled-sleeper-auto-refresh.md)). A poison/failing event that exhausts
  Lambda's async retries is routed to an SQS dead-letter queue (`leagueql-onboarder-dlq-{env}`,
  prod only) instead of being silently dropped, preserving the full payload (incl.
  `correlation_id`) for inspection and replay. Any message in the DLQ raises a CloudWatch alarm.
- **Auction vs. snake drafts:** both ESPN and Sleeper auction drafts must be handled
  (`bid_amount`, `nominating_team_id` populated for auction picks).
- **Invalid `leagueId` format:** must match `^\d+$`; otherwise `422`.
- **Subscription end time:** onboarding never writes `subscription_end_time`. A freshly
  onboarded league has no subscription attribute and reads as **expired** until the Stripe
  billing webhook sets it server-side after checkout (see
  [BE-014](BE-014-subscription-access-control.md) / [BE-015](BE-015-stripe-billing.md)). The
  former client-supplied `subscriptionEndTime` request field has been **removed** — it was a
  spoofable stopgap that allowed self-granting a subscription and bypassing billing.

## Acceptance Criteria
- [ ] `POST /leagues?requestType=ONBOARD` with a valid, not-yet-onboarded league returns
      `201` with `{ detail, data: { correlation_id } }` and invokes the onboarder Lambda.
- [ ] A duplicate `ONBOARD` for an already-onboarded league returns `200` and does not
      re-trigger the pipeline.
- [ ] ESPN onboards require `season`; private ESPN leagues require `s2` + `swid`.
- [ ] `s2` / `swid` cookie values never appear in logs or persisted DynamoDB/S3 items.
- [ ] On success: a canonical league UUID, `METADATA`, per-platform `LEAGUE_LOOKUP`, and
      all precomputed view items exist; `LEAGUE_COUNT` is incremented by 1.
- [ ] Onboarding never writes `subscription_end_time`; a freshly onboarded league's `METADATA`
      item carries no subscription attribute (it is set only by the Stripe webhook —
      [BE-015](BE-015-stripe-billing.md)). The request body has no `subscriptionEndTime` field.
- [ ] The Sleeper `previous_league_id` chain walk terminates at the founding season for
      both terminator forms — string `"0"` and JSON `null` (`None`) — and never issues a
      request for league `None`.
- [ ] A Sleeper season with `status` of `pre_draft` or `drafting` is excluded from the
      onboarded season list and produces no S3 payload, no processed views, and no dropdown
      entry; a Sleeper onboard whose only season is not-yet-started fails with `NOT_STARTED`.
- [ ] Raw platform API payloads are written to S3 under `raw-api-data/{canonical_league_id}/`.
- [ ] On any failure a `JOB_STATUS` item is written with `status=FAILED` and a
      `failure_code` / `failure_reason` that the frontend can surface.
- [ ] A `JOB_STATUS` item keyed by `correlation_id` is created so the frontend can poll
      [BE-008](BE-008-job-status-tracking.md).
- [ ] When an async onboarder invocation exhausts its retries, the failed event is delivered
      to the onboarder DLQ (not dropped) and a CloudWatch alarm fires on DLQ depth > 0.

## Authorization (BE-016)
First ONBOARD records the onboarding Clerk user as the league **owner** (`owner_user_id`) and seeds the `members` set — the authorization anchor for [BE-016](BE-016-league-ownership-authorization.md). REFRESH/MIGRATE never overwrite it.

## Sources
`src/api/routes.py`, `src/onboarder/`, `docs/api/openapi_spec.yaml`, `docs/db/dynamodb_spec.md`.
