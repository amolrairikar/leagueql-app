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
  `s2`/`swid` (private ESPN only), `subscriptionEndTime` (optional, interim — see
  [BE-015](BE-015-stripe-billing.md))).

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
- **Subscription end time (interim):** when `subscriptionEndTime` is supplied, it is
  persisted on the `METADATA` item as `subscription_end_time`; when absent, no subscription
  attribute is written (the league reads as expired until billing sets one — see
  [BE-014](BE-014-subscription-access-control.md)). This is a **client-supplied, spoofable
  stopgap**: the authoritative value is set server-side by the Stripe billing webhook, and
  this onboarding input is removed once [BE-015](BE-015-stripe-billing.md) lands.

## Acceptance Criteria
- [ ] `POST /leagues?requestType=ONBOARD` with a valid, not-yet-onboarded league returns
      `201` with `{ detail, data: { correlation_id } }` and invokes the onboarder Lambda.
- [ ] A duplicate `ONBOARD` for an already-onboarded league returns `200` and does not
      re-trigger the pipeline.
- [ ] ESPN onboards require `season`; private ESPN leagues require `s2` + `swid`.
- [ ] `s2` / `swid` cookie values never appear in logs or persisted DynamoDB/S3 items.
- [ ] On success: a canonical league UUID, `METADATA`, per-platform `LEAGUE_LOOKUP`, and
      all precomputed view items exist; `LEAGUE_COUNT` is incremented by 1.
- [ ] When `subscriptionEndTime` is supplied, the `METADATA` item carries
      `subscription_end_time`; when absent, no subscription attribute is written.
- [ ] Raw platform API payloads are written to S3 under `raw-api-data/{canonical_league_id}/`.
- [ ] On any failure a `JOB_STATUS` item is written with `status=FAILED` and a
      `failure_code` / `failure_reason` that the frontend can surface.
- [ ] A `JOB_STATUS` item keyed by `correlation_id` is created so the frontend can poll
      [BE-008](BE-008-job-status-tracking.md).
- [ ] When an async onboarder invocation exhausts its retries, the failed event is delivered
      to the onboarder DLQ (not dropped) and a CloudWatch alarm fires on DLQ depth > 0.

## Sources
`src/api/routes.py`, `src/onboarder/`, `docs/api/openapi_spec.yaml`, `docs/db/dynamodb_spec.md`.
