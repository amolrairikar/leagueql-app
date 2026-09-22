import json
import uuid
from collections import defaultdict

from utils import (
    get_leagues_to_refresh,
    get_nfl_state,
    invoke_onboarder_lambda,
    logger,
    pace_dispatch,
)

from common.tracing import init_tracing, traced_handler

# Originate a trace per refreshed league → Better Stack (backend/otel-tracing); the onboarder/
# processor continue it. A no-op unless tracing is configured, so tests /
# unconfigured envs are unaffected.
init_tracing("leagueql-league-refresh")


def lambda_handler(event, context) -> dict[str, str | int]:
    """
    Main handler function for the multi-platform league refresh.

    Args:
        event: The event data that triggered the Lambda function.
        context: The context in which the Lambda function is running.

    Returns:
        dict: A response indicating the success of the operation.
    """
    logger.info("Starting league refresh execution.")
    logger.info("Event data: %s", event)
    logger.info(
        "Context data: request_id=%s, function_name=%s",
        context.aws_request_id,
        context.function_name,
    )

    # Fetch current NFL state. Raise on failure so the Lambda's Errors metric
    # increments and the league_refresh_errors alarm fires — otherwise the
    # scheduled run would report success while refreshing nothing.
    try:
        nfl_state = get_nfl_state()
    except Exception:
        logger.error("Failed to fetch NFL state", exc_info=True)
        raise

    # Check if season_type is "off" or week is 1
    season_type = nfl_state.get("season_type")
    week = nfl_state.get("week")

    if season_type == "off":
        logger.info("NFL season_type is 'off', skipping refresh")
        return {
            "statusCode": 200,
            "body": json.dumps(
                {"status": "skipped", "message": "NFL season is off-season"}
            ),
        }

    if week == 1:
        logger.info("NFL week is 1, skipping refresh")
        return {
            "statusCode": 200,
            "body": json.dumps(
                {"status": "skipped", "message": "Week 1 - matchups not settled yet"}
            ),
        }

    # Resolve the current NFL season, which gates league selection (leagues onboarded
    # only through a completed prior season are skipped). Treat a missing/unparseable
    # season as indeterminate NFL state and raise (see NFL-state note above) rather
    # than refreshing without a current-season reference.
    try:
        current_season = int(nfl_state["season"])
    except (KeyError, TypeError, ValueError):
        logger.error("NFL state missing a parseable 'season': %s", nfl_state)
        raise

    logger.info(
        "NFL state: season_type=%s, week=%s, season=%s, proceeding with refresh",
        season_type,
        week,
        current_season,
    )

    # Query DynamoDB for all Sleeper and Yahoo leagues. Raise on failure (see NFL-state
    # note above) so a query failure that refreshes zero leagues trips the error alarm.
    try:
        leagues = get_leagues_to_refresh(current_season)
    except Exception:
        logger.error("Failed to fetch leagues from DynamoDB", exc_info=True)
        raise

    if not leagues:
        logger.info("No leagues found to refresh")
        return {
            "statusCode": 200,
            "body": json.dumps(
                {"status": "succeeded", "message": "No leagues to refresh"}
            ),
        }

    logger.info("Found %d leagues to refresh", len(leagues))

    # Group by platform so pacing is applied within a platform's dispatches (the
    # per-platform API is what we protect from a burst).
    leagues_by_platform = defaultdict(list)
    for league in leagues:
        leagues_by_platform[league["platform"]].append(league)

    success_count = 0
    failure_count = 0

    for platform, platform_leagues in leagues_by_platform.items():
        for index, league in enumerate(platform_leagues):
            # Pace between consecutive same-platform dispatches (not before the first,
            # and not between platform groups) so the fanned-out onboarders don't hit
            # a platform's API all at once.
            if index > 0:
                pace_dispatch()

            correlation_id = str(uuid.uuid4())
            # Each league gets its own root trace (the cron has no inbound context); the
            # active span is what propagates to the onboarder via the invoke payload.
            with traced_handler("league_refresh.league", root=True) as span:
                if span is not None:
                    span.set_attribute("platform", platform)
                try:
                    invoke_onboarder_lambda(
                        league["league_id"],
                        canonical_league_id=league["canonical_league_id"],
                        correlation_id=correlation_id,
                        platform=platform,
                        owner_user_id=league["owner_user_id"],
                        season=league.get("season"),
                    )
                    success_count += 1
                    logger.info(
                        "Successfully triggered refresh for %s league %s with correlation_id %s",
                        platform,
                        league["league_id"],
                        correlation_id,
                    )
                except Exception as e:  # noqa: BLE001 — isolate one league's failure
                    failure_count += 1
                    logger.error(
                        "Failed to trigger refresh for %s league %s: %s",
                        platform,
                        league["league_id"],
                        e,
                    )

    logger.info(
        "Refresh complete: %d succeeded, %d failed",
        success_count,
        failure_count,
    )

    # A dispatch failure means the onboarder was never invoked for that league, so
    # neither the onboarder error alarm nor its DLQ would catch it. Raise so the
    # Lambda's own Errors alarm fires (and EventBridge retries the run, re-attempting
    # the failed dispatches).
    if failure_count > 0:
        raise RuntimeError(
            f"Failed to trigger refresh for {failure_count} of {len(leagues)} leagues"
        )

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "status": "succeeded",
                "total_leagues": len(leagues),
                "success_count": success_count,
                "failure_count": failure_count,
            }
        ),
    }
