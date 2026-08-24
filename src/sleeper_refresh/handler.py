import json
import uuid

from common.tracing import init_tracing, traced_handler
from utils import logger, get_nfl_state, get_sleeper_leagues, invoke_onboarder_lambda

# Originate a trace per refreshed league → Better Stack (backend/otel-tracing); the onboarder/
# processor continue it. A no-op unless tracing is configured, so tests /
# unconfigured envs are unaffected.
init_tracing("leagueql-sleeper-refresh")


def lambda_handler(event, context) -> dict[str, str | int]:
    """
    Main handler function for Sleeper refresh.

    Args:
        event: The event data that triggered the Lambda function.
        context: The context in which the Lambda function is running.

    Returns:
        dict: A response indicating the success of the operation.
    """
    logger.info("Starting Sleeper refresh execution.")
    logger.info("Event data: %s", event)
    logger.info(
        "Context data: request_id=%s, function_name=%s",
        context.aws_request_id,
        context.function_name,
    )

    # Fetch current NFL state. Raise on failure so the Lambda's Errors metric
    # increments and the sleeper_refresh_errors alarm fires — otherwise the
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

    logger.info(
        "NFL state: season_type=%s, week=%s, proceeding with refresh", season_type, week
    )

    # Query DynamoDB for all Sleeper leagues. Raise on failure (see NFL-state note
    # above) so a query failure that refreshes zero leagues trips the error alarm.
    try:
        sleeper_leagues = get_sleeper_leagues()
    except Exception:
        logger.error("Failed to fetch Sleeper leagues from DynamoDB", exc_info=True)
        raise

    if not sleeper_leagues:
        logger.info("No Sleeper leagues found in DynamoDB")
        return {
            "statusCode": 200,
            "body": json.dumps(
                {"status": "succeeded", "message": "No Sleeper leagues to refresh"}
            ),
        }

    logger.info("Found %d Sleeper leagues to refresh", len(sleeper_leagues))

    # Invoke onboarder lambda for each league
    success_count = 0
    failure_count = 0

    for league in sleeper_leagues:
        correlation_id = str(uuid.uuid4())
        # Each league gets its own root trace (the cron has no inbound context); the
        # active span is what propagates to the onboarder via the invoke payload.
        with traced_handler("sleeper_refresh.league", root=True):
            try:
                invoke_onboarder_lambda(
                    league["league_id"],
                    canonical_league_id=league["canonical_league_id"],
                    correlation_id=correlation_id,
                )
                success_count += 1
                logger.info(
                    "Successfully triggered refresh for league %s with correlation_id %s",
                    league["league_id"],
                    correlation_id,
                )
            except Exception as e:
                failure_count += 1
                logger.error(
                    "Failed to trigger refresh for league %s: %s",
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
            f"Failed to trigger refresh for {failure_count} of "
            f"{len(sleeper_leagues)} Sleeper leagues"
        )

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "status": "succeeded",
                "total_leagues": len(sleeper_leagues),
                "success_count": success_count,
                "failure_count": failure_count,
            }
        ),
    }
