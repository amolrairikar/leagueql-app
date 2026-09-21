# Proposal

## Why

The scheduled auto-refresher is Sleeper-only: it enumerates Sleeper leagues and invokes the
onboarder in `REFRESH` mode for each, in a tight loop with zero delay. Yahoo leagues can now be
auto-refreshed through the same onboarder contract, but nothing refreshes them on a schedule, and
dispatching every league at once makes the downstream onboarders hit a platform's API
simultaneously — a burst that risks throttling (Yahoo throttles aggressively).

## What Changes

- Generalize the single scheduled refresher to refresh onboarded **Sleeper and Yahoo** leagues in
  one run (ESPN still excluded — it requires user-supplied cookies).
- For Yahoo, resolve each canonical league's owner (`owner_user_id`, which lives only on the
  `METADATA` item) and pass it in the onboarder invoke so the onboarder can obtain/refresh that
  owner's OAuth token; **skip** any Yahoo league whose `METADATA` has no `owner_user_id`.
- Add configurable **interval + random jitter pacing** between consecutive dispatches to the same
  platform, so the fanned-out onboarders don't hit a platform API all at once.
- Keep Sleeper-only behaviors intact: pending-renewal polling, most-recent-season de-duplication,
  and stale-season skipping.
- Preserve the existing operational contract: NFL-state gating (skip offseason / week 1), raise on
  indeterminate NFL state or a league-list query failure, and per-league failure isolation with a
  raise-after-loop so the run is retried.
- **Rename** the capability `scheduled-sleeper-auto-refresh` → `scheduled-league-auto-refresh` (and
  the underlying Lambda/module/infra) to reflect its multi-platform scope.

## Capabilities

### New Capabilities
- `backend/scheduled-league-auto-refresh`: Scheduled Lambda that automatically refreshes onboarded
  Sleeper and Yahoo leagues during the NFL season, resolving the Yahoo owner from `METADATA`,
  pacing dispatches per platform, and invoking the onboarder in `REFRESH` mode for each.

### Modified Capabilities
<!-- None modified in place; the Sleeper-specific capability is renamed (removed + re-added below). -->

### Removed Capabilities
- `backend/scheduled-sleeper-auto-refresh`: Superseded by `backend/scheduled-league-auto-refresh`;
  its requirements are generalized and moved to the new capability (a rename, not a behavior loss).

## Impact

- **Code:** `src/sleeper_refresh/` → `src/league_refresh/` (handler + utils); reuses the existing
  shared `src/common/onboarder_invoke.py` (already accepts `owner_user_id`) and
  `src/common/tracing.py`. No change to the onboarder or `common.yahoo_tokens` — all Yahoo token
  work stays downstream in the onboarder.
- **Infra (Terraform):** rename the refresher Lambda, EventBridge rule/target/permission, error
  alarm, and IAM role (`leagueql-sleeper-refresh-*`/`sleeper-league-refresh-role` →
  `leagueql-league-refresh-*`/`league-refresh-lambda-role`); add `dynamodb:GetItem` (for the Yahoo
  `METADATA` owner lookup); add pacing env vars; raise the Lambda timeout for paced dispatch.
  Terraform recreates the renamed resources on apply (no data loss; brief gap in the weekly cron).
- **Build/CI:** update the Lambda-zip source path in `.github/workflows/build.yaml`.
- **Docs:** update `docs/architecture/architecture_diagram.py` (refresher node label) and regenerate
  the PNG. No DynamoDB/API schema change (the `METADATA` `owner_user_id` field already exists).
- **Tests:** rename/generalize the unit (`tests/unit/sleeper_refresh/`), component
  (`tests/component/.../sleeper_auto_refresh.feature` + steps), and Sleeper integration suites; add
  Yahoo enumeration/owner-resolution/skip cases and dispatch-pacing cases.
- **No breaking changes** to any external API; DynamoDB access pattern is unchanged except an added
  point read of an existing item.
