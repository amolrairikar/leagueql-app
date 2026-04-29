import json

from utils import logger, get_nfl_state, get_sleeper_leagues, invoke_onboarder_lambda


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
    logger.info("Context data: %s", context)

    # Fetch current NFL state
    try:
        nfl_state = get_nfl_state()
    except Exception as e:
        logger.error("Failed to fetch NFL state: %s", e)
        return {
            "statusCode": 502,
            "body": json.dumps({"status": "failed", "error_msg": str(e)}),
        }

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

    # Query DynamoDB for all Sleeper leagues
    try:
        sleeper_leagues = get_sleeper_leagues()
    except Exception as e:
        logger.error("Failed to fetch Sleeper leagues from DynamoDB: %s", e)
        return {
            "statusCode": 500,
            "body": json.dumps({"status": "failed", "error_msg": str(e)}),
        }

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
    failures = []

    for league_id in sleeper_leagues:
        try:
            invoke_onboarder_lambda(league_id)
            success_count += 1
            logger.info("Successfully triggered refresh for league %s", league_id)
        except Exception as e:
            failure_count += 1
            failures.append({"league_id": league_id, "error": str(e)})
            logger.error("Failed to trigger refresh for league %s: %s", league_id, e)

    logger.info(
        "Refresh complete: %d succeeded, %d failed",
        success_count,
        failure_count,
    )

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "status": "succeeded",
                "total_leagues": len(sleeper_leagues),
                "success_count": success_count,
                "failure_count": failure_count,
                "failures": failures,
            }
        ),
    }
