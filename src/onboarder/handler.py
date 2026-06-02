import json
import uuid

import requests

from common.job_status import classify_http_error, write_job_status
from onboarding_service import OnboardingService
from sleeper_client import resolve_sleeper_canonical_league_id
from utils import correlation_id_var, logger, publish_failure


def _record_failure(
    request_type: str,
    failure_code: str,
    body: dict | None = None,
    canonical_league_id: str | None = None,
) -> None:
    """Write a FAILED JOB_STATUS item so the failure reaches the user (best-effort)."""
    body = body or {}
    league_id = body.get("leagueId")
    write_job_status(
        correlation_id_var.get(),
        "FAILED",
        request_type or "ONBOARD",
        failure_code=failure_code,
        league_id=str(league_id) if league_id else None,
        platform=body.get("platform"),
        canonical_league_id=canonical_league_id,
    )


def lambda_handler(event, context) -> dict[str, str | int]:
    """
    Main handler function for league onboarder.

    Args:
        event: The event data that triggered the Lambda function.
        context: The context in which the Lambda function is running.

    Returns:
        dict: A response indicating the success of the operation.
    """
    correlation_id = event.get("correlation_id") or str(uuid.uuid4())
    correlation_id_var.set(correlation_id)

    try:
        body = event["body"]
        request_type = event["requestType"]
    except KeyError as e:
        logger.error("Missing required field in event: %s", e)
        return {
            "statusCode": 400,
            "body": json.dumps(
                {
                    "status": "failed",
                    "error_msg": f"Missing required event field: {e}",
                }
            ),
        }
    # NOTE: We cannot log the event due to the potential for sensitive ESPN cookies
    logger.info(
        "Starting league onboarding: request_type=%s platform=%s league_id=%s",
        event.get("requestType"),
        event.get("body", {}).get("platform"),
        event.get("body", {}).get("leagueId"),
    )
    logger.info("Context data: %s", context)

    canonical_league_id = event.get("canonicalLeagueId")
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
            publish_failure(str(e))
            _record_failure(request_type, classify_http_error(e), body)
            return {
                "statusCode": 502,
                "body": json.dumps(
                    {
                        "status": "failed",
                        "error_msg": "An upstream service error occurred.",
                    }
                ),
            }
        except Exception as e:
            logger.error(
                "Unexpected error resolving Sleeper canonical league ID: %s", e
            )
            publish_failure(str(e))
            _record_failure(request_type, "INTERNAL", body)
            return {
                "statusCode": 500,
                "body": json.dumps(
                    {
                        "status": "failed",
                        "error_msg": "An internal server error occurred.",
                    }
                ),
            }

        if not canonical_league_id:
            logger.warning(
                "Could not resolve canonical league ID for Sleeper league %s; league has not been onboarded",
                body.get("leagueId"),
            )
            _record_failure(request_type, "NOT_FOUND", body)
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
        logger.info(
            "Resolved canonical_league_id=%s for new Sleeper season; is_new_season_refresh=True",
            canonical_league_id,
        )

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
        _record_failure(request_type, "INVALID_INPUT", body, canonical_league_id)
        return {
            "statusCode": 400,
            "body": json.dumps({"status": "failed", "error_msg": str(e)}),
        }
    except ValueError as e:
        logger.error(
            "Incorrect value error while initializing onboarding service: %s", e
        )
        _record_failure(request_type, "INVALID_INPUT", body, canonical_league_id)
        return {
            "statusCode": 400,
            "body": json.dumps({"status": "failed", "error_msg": str(e)}),
        }
    except requests.exceptions.HTTPError as e:
        logger.error(
            "Request error occurred fetching data while initializing onboarding service: %s",
            e,
        )
        publish_failure(str(e))
        _record_failure(request_type, classify_http_error(e), body, canonical_league_id)
        return {
            "statusCode": 502,
            "body": json.dumps(
                {
                    "status": "failed",
                    "error_msg": "An upstream service error occurred.",
                }
            ),
        }
    except RuntimeError as e:
        logger.error(
            "Runtime error occurred while initializing onboarding service: %s", e
        )
        publish_failure(str(e))
        _record_failure(request_type, "UPSTREAM", body, canonical_league_id)
        return {
            "statusCode": 502,
            "body": json.dumps(
                {
                    "status": "failed",
                    "error_msg": "An upstream service error occurred.",
                }
            ),
        }

    logger.info(
        "OnboardingService initialized: canonical_league_id=%s",
        onboarding_service.canonical_league_id,
    )
    try:
        onboarding_service.run()
    except KeyError as e:
        logger.error("Missing required environment variable: %s", e)
        publish_failure(str(e))
        _record_failure(
            request_type, "INTERNAL", body, onboarding_service.canonical_league_id
        )
        return {
            "statusCode": 500,
            "body": json.dumps(
                {
                    "status": "failed",
                    "error_msg": "An internal server error occurred.",
                }
            ),
        }
    except requests.exceptions.HTTPError as e:
        logger.error("HTTP error occurred while running onboarding service: %s", e)
        publish_failure(str(e))
        _record_failure(
            request_type,
            classify_http_error(e),
            body,
            onboarding_service.canonical_league_id,
        )
        return {
            "statusCode": 502,
            "body": json.dumps(
                {
                    "status": "failed",
                    "error_msg": "An upstream service error occurred.",
                }
            ),
        }
    except RuntimeError as e:
        logger.error("Runtime error occurred while running onboarding service: %s", e)
        publish_failure(str(e))
        _record_failure(
            request_type, "UPSTREAM", body, onboarding_service.canonical_league_id
        )
        return {
            "statusCode": 502,
            "body": json.dumps(
                {
                    "status": "failed",
                    "error_msg": "An upstream service error occurred.",
                }
            ),
        }
    except Exception as e:
        logger.error(
            "Unexpected error occurred while running onboarding service: %s", e
        )
        publish_failure(str(e))
        _record_failure(
            request_type, "INTERNAL", body, onboarding_service.canonical_league_id
        )
        return {
            "statusCode": 500,
            "body": json.dumps(
                {
                    "status": "failed",
                    "error_msg": "An internal server error occurred.",
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
