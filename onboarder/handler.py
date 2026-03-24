import json

import requests

from onboarding_service import OnboardingService
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
    # NOTE: We cannot log the event due to the potential for sensitive ESPN cookies
    logger.info("Starting league onboarding process execution.")
    logger.info("Context data: %s", context)

    try:
        service = OnboardingService(
            league_id=str(body["leagueId"]),
            platform=body["platform"],
            latest_season=body.get("season"),
            espn_s2_cookie=body.get("s2"),
            swid_cookie=body.get("swid"),
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
        job_id = service.run()
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
        "body": json.dumps({"status": "succeeded", "onboarding_job_id": job_id}),
    }
