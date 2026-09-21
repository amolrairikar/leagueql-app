# Design

## Context

See proposal.md — Why. The current refresher (`src/sleeper_refresh/`) queries `GSI2` for
`platform = "SLEEPER"`, groups `LEAGUE_LOOKUP` items by canonical league, and fire-and-forget
async-invokes the onboarder (`InvocationType="Event"`, via `common.onboarder_invoke.invoke_onboarder`)
in `REFRESH` mode, in a tight loop with no delay. The onboarder already supports Yahoo `REFRESH`
through the same invoke contract, but needs an `ownerUserId` to obtain/refresh the owner's Yahoo
OAuth token; that field lives only on the `METADATA` item (`PK=LEAGUE#{canonical}, SK=METADATA`),
not on the `LEAGUE_LOOKUP` items `GSI2` returns.

## Goals / Non-Goals

**Goals:**
- One scheduled run refreshes both Sleeper and Yahoo leagues, reusing the existing invoke contract.
- Resolve the Yahoo owner from `METADATA` and skip Yahoo leagues that have none.
- Space same-platform dispatches with a configurable interval + jitter so onboarders don't burst a
  platform API.
- Preserve every existing operational guarantee (NFL gating, pending-renewal polling, raise-on-error,
  per-league isolation).

**Non-Goals:**
- No Yahoo token handling in the refresher — that stays in the onboarder (`common.yahoo_tokens`).
- No pre-flight `has_valid_link` check in the refresher (would require KMS access); a revoked link
  surfaces inside the onboarder and is handled by its existing error path/DLQ.
- No Yahoo "pending renewal" polling (Sleeper-only concept; Yahoo has no `pending_season` marker).
- No change to the EventBridge schedule cadence or to ESPN handling.

## Decisions

- **Single Lambda, per-platform enumeration.** Generalize `get_sleeper_leagues` into
  `get_leagues_to_refresh(current_season)` that queries `GSI2` once per platform (`SLEEPER`, then
  `YAHOO`) and returns dicts carrying `platform`, `league_id`, `canonical_league_id`, and
  `owner_user_id`. Reuses the existing most-recent-season / stale-season logic for both platforms.
  Alternative considered: enumerate Yahoo via `GSI3` (METADATA) to get the owner in one query — but
  `GSI3` lacks the platform `league_id`, so a `GSI2` query + per-canonical `GetItem` on `METADATA`
  is simpler and mirrors the existing Sleeper path.

- **Owner resolution via point read.** For each surviving Yahoo canonical, `GetItem` the `METADATA`
  item and read `owner_user_id`; skip (with a log line) if absent. This adds one `dynamodb:GetItem`
  permission on the table (the table ARN is already a resource on the role's DynamoDB statement).

- **Pacing = interval + jitter, in the refresher.** Because dispatch is an async invoke, sleeping in
  the refresher between consecutive same-platform dispatches directly staggers when each onboarder
  hits the platform API. Base interval `REFRESH_DISPATCH_INTERVAL_SECONDS` (default 3) plus
  `random.uniform(0, REFRESH_DISPATCH_JITTER_SECONDS)` (default 5). No sleep after a platform's last
  dispatch or between platform groups. Env-configurable so it can be retuned without a code change.
  Alternative considered: scheduling staggered invocations or per-platform SQS with delivery delay —
  heavier infra for a job with modest league counts.

- **Timeout sized for pacing.** With paced sleeps the run can exceed the current 60s timeout, so
  raise the Lambda timeout to 900s (memory unchanged at 512). Runtime is dominated by sleeps, not CPU.

- **Rename over in-place generalize.** Rename `sleeper_refresh` → `league_refresh` across module,
  Lambda, EventBridge rule/alarm/IAM role, spec, and tests so names aren't misleading. Accepts a
  Terraform destroy+create of those resources on apply (no data loss; brief gap in the weekly cron).

## Risks / Trade-offs

- **Terraform recreates renamed resources** → destroy+create on apply; no persistent state on these
  resources, and the cron is weekly, so the exposure is a short window. Documented in the migration plan.
- **Revoked Yahoo link produces a downstream onboarder failure** (not a refresher failure) → accepted;
  it's caught by the onboarder's existing error handling/DLQ, exactly like any onboarder-side error.
  The refresher only tracks the 202 dispatch ack, unchanged from today.
- **Yahoo season-id churn** (Yahoo mints a new numeric `league_id` each season) → out of scope here;
  the refresher passes the stored most-recent `league_id`, and the onboarder's Yahoo `REFRESH` path
  resolves the current season from the owner's live league list. Noted as a follow-up if it proves
  insufficient.
- **Long timeout with large league counts** → at modest counts the 900s ceiling is ample; if counts
  grow substantially, revisit batching or fan-out. Interval/jitter are env-tunable to keep runtime bounded.

## Migration Plan

- Ship code + infra in one change. On `terraform apply`, the old `sleeper_refresh` Lambda/rule/alarm/role
  are destroyed and the `league_refresh` equivalents created; the CI Lambda-zip path switches to
  `src/league_refresh`. No data migration (no persistent state on these resources).
- Rollback: revert the change; Terraform recreates the Sleeper-named resources. DynamoDB data is untouched.
