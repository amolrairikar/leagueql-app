import json

import requests

from onboarding_service import OnboardingService
from sleeper_client import resolve_sleeper_canonical_league_id
from utils import logger


def lambda_handler(event, context) -> dict[str, str | int]:
    """
    Main handler function for league onboarder.

    Args:
        event: The event data that triggered the Lambda function.
        context: The context in which the Lambda function is running.

    Returns:
        dict: A response indicating the success of the operation.
    """
    body = event["body"]
    request_type = event["requestType"]
    # NOTE: We cannot log the event due to the potential for sensitive ESPN cookies
    logger.info("Starting league onboarding process execution.")
    logger.info("Context data: %s", context)

    canonical_league_id = event.get("canonicalLeagueId", None)
    is_new_season_refresh = False

    if (
        request_type == "REFRESH"
        and not canonical_league_id
        and body.get("platform") == "SLEEPER"
    ):
        logger.info(
            "Sleeper REFRESH received with no canonical league ID; walking previous_league_id chain for league %s",
            body.get("leagueId"),
        )
        try:
            canonical_league_id = resolve_sleeper_canonical_league_id(
                new_league_id=str(body["leagueId"])
            )
        except requests.exceptions.HTTPError as e:
            logger.error("HTTP error resolving Sleeper canonical league ID: %s", e)
            return {
                "statusCode": 502,
                "body": json.dumps({"status": "failed", "error_msg": str(e)}),
            }
        except Exception as e:
            logger.error(
                "Unexpected error resolving Sleeper canonical league ID: %s", e
            )
            return {
                "statusCode": 500,
                "body": json.dumps({"status": "failed", "error_msg": str(e)}),
            }

        if not canonical_league_id:
            logger.warning(
                "Could not resolve canonical league ID for Sleeper league %s; league has not been onboarded",
                body.get("leagueId"),
            )
            return {
                "statusCode": 404,
                "body": json.dumps(
                    {
                        "status": "failed",
                        "error_msg": f"League {body.get('leagueId')} has not been onboarded on SLEEPER platform",
                    }
                ),
            }
        is_new_season_refresh = True

    try:
        onboarding_service = OnboardingService(
            league_id=str(body["leagueId"]),
            platform=body["platform"],
            latest_season=body.get("season"),
            espn_s2_cookie=body.get("s2"),
            swid_cookie=body.get("swid"),
            request_type=request_type,
            canonical_league_id=canonical_league_id,
            is_new_season_refresh=is_new_season_refresh,
        )
    except KeyError as e:
        logger.error("Missing required field in request body: %s", e)
        return {
            "statusCode": 400,
            "body": json.dumps({"status": "failed", "error_msg": str(e)}),
        }
    except ValueError as e:
        logger.error(
            "Incorrect value error while initializing onboarding service: %s", e
        )
        return {
            "statusCode": 400,
            "body": json.dumps({"status": "failed", "error_msg": str(e)}),
        }
    except requests.exceptions.HTTPError as e:
        logger.error(
            "Request error occurred fetching data while initializing onboarding service: %s",
            e,
        )
        return {
            "statusCode": 502,
            "body": json.dumps({"status": "failed", "error_msg": str(e)}),
        }
    except RuntimeError as e:
        logger.error(
            "Runtime error occurred while initializing onboarding service: %s", e
        )
        return {
            "statusCode": 502,
            "body": json.dumps({"status": "failed", "error_msg": str(e)}),
        }

    try:
        onboarding_service.run()
    except KeyError as e:
        logger.error("Missing required environment variable: %s", e)
        return {
            "statusCode": 400,
            "body": json.dumps({"status": "failed", "error_msg": str(e)}),
        }
    except RuntimeError as e:
        logger.error("Runtime error occurred while running onboarding service: %s", e)
        return {
            "statusCode": 502,
            "body": json.dumps({"status": "failed", "error_msg": str(e)}),
        }
    except Exception as e:
        logger.error(
            "Unexpected error occurred while running onboarding service: %s", e
        )
        return {
            "statusCode": 500,
            "body": json.dumps(
                {
                    "status": "failed",
                    "error_msg": f"Unexpected error occurred: {str(e)}",
                }
            ),
        }

    logger.info("Ending league onboarding process execution.")
    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "status": "succeeded",
                "canonical_league_id": onboarding_service.canonical_league_id,
            }
        ),
    }
