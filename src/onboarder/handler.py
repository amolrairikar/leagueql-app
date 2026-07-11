import json
import uuid

import requests

from common.job_status import (
    SYSTEMIC_FAILURE_CODES,
    classify_http_error,
    write_job_status,
)
from common.tracing import init_tracing, traced_handler
from onboarding_service import OnboardingService
from sleeper_client import resolve_sleeper_canonical_league_id
from utils import correlation_id_var, logger, publish_failure

# Continue the trace started upstream (API or Sleeper refresh) → Axiom (BE-020).
# A no-op unless Axiom is configured, so tests / unconfigured envs are unaffected.
init_tracing("leagueql-onboarder")


def _record_failure(
    request_type: str,
    failure_code: str,
    body: dict | None = None,
    canonical_league_id: str | None = None,
    error_detail: str | None = None,
) -> None:
    """Write a FAILED JOB_STATUS item so the failure reaches the user (best-effort).

    Systemic failure codes (see ``SYSTEMIC_FAILURE_CODES`` — our fault / actionable)
    additionally publish an SNS alert. Expected user errors (INVALID_INPUT,
    ESPN_AUTH, NOT_FOUND) are recorded for the user but never page us. Centralizing
    the decision here keeps it keyed off the classified ``failure_code``, so an
    HTTPError classified as ESPN_AUTH/NOT_FOUND no longer triggers an alert.
    """
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
    if failure_code in SYSTEMIC_FAILURE_CODES:
        publish_failure(
            error_detail or f"{request_type or 'ONBOARD'} failed: {failure_code}"
        )


def lambda_handler(event, context) -> dict[str, str | int]:
    """Entry point: continue the upstream trace (BE-020), then run the onboarder.

    Wraps :func:`_handle` in a span that continues the trace carried in
    ``event["trace_context"]`` (a no-op when tracing is disabled) and force-flushes
    spans before returning, since the Lambda freezes between invocations.

    Args:
        event: The event data that triggered the Lambda function.
        context: The context in which the Lambda function is running.

    Returns:
        dict: A response indicating the success of the operation.
    """
    with traced_handler("onboarder.handle", carrier=event.get("trace_context")):
        return _handle(event, context)


def _handle(event, context) -> dict[str, str | int]:
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

    # Sleeper renews a league each season under a brand-new league ID linked back to the
    # prior season via previous_league_id. When we don't already know the canonical league
    # — for either an ONBOARD or a REFRESH — walk that chain to see whether this ID is a
    # renewal of a league we have already onboarded (BE-001 / BE-002):
    #   * chain resolves an existing canonical -> the league is already onboarded and this
    #     is just a new season to register, so fold it into the new-season-refresh path
    #     (register the new league ID's LEAGUE_LOOKUP against the existing canonical and
    #     never write a second METADATA record);
    #   * no match on ONBOARD -> a genuinely new league; fall through and mint a canonical;
    #   * no match on REFRESH -> the league was never onboarded; 404 as before.
    if (
        request_type in ("ONBOARD", "REFRESH")
        and not canonical_league_id
        and body.get("platform") == "SLEEPER"
    ):
        logger.info(
            "Sleeper %s received with no canonical league ID; walking previous_league_id chain for league %s",
            request_type,
            body.get("leagueId"),
        )
        try:
            canonical_league_id = resolve_sleeper_canonical_league_id(
                new_league_id=str(body["leagueId"])
            )
        except requests.exceptions.HTTPError as e:
            logger.error("HTTP error resolving Sleeper canonical league ID: %s", e)
            _record_failure(
                request_type, classify_http_error(e), body, error_detail=str(e)
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
                "Unexpected error resolving Sleeper canonical league ID: %s", e
            )
            _record_failure(request_type, "INTERNAL", body, error_detail=str(e))
            return {
                "statusCode": 500,
                "body": json.dumps(
                    {
                        "status": "failed",
                        "error_msg": "An internal server error occurred.",
                    }
                ),
            }

        if canonical_league_id:
            # Already-onboarded league, new season. Reuse the existing canonical and take
            # the new-season-refresh write path so the original METADATA (owner, members,
            # onboarded_at) is preserved instead of overwritten — an ONBOARD of a renewal
            # is handled exactly like a refresh.
            is_new_season_refresh = True
            request_type = "REFRESH"
            logger.info(
                "Resolved canonical_league_id=%s for new Sleeper season; handling as new-season refresh (is_new_season_refresh=True)",
                canonical_league_id,
            )
        elif request_type == "REFRESH":
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
        else:
            logger.info(
                "Sleeper league %s is not a renewal of an onboarded league; proceeding as a new onboard",
                body.get("leagueId"),
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
            owner_user_id=event.get("ownerUserId"),
            reprocess_all=bool(event.get("reprocessAll")),
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
        _record_failure(
            request_type,
            classify_http_error(e),
            body,
            canonical_league_id,
            error_detail=str(e),
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
        logger.error(
            "Runtime error occurred while initializing onboarding service: %s", e
        )
        _record_failure(
            request_type, "UPSTREAM", body, canonical_league_id, error_detail=str(e)
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

    logger.info(
        "OnboardingService initialized: canonical_league_id=%s",
        onboarding_service.canonical_league_id,
    )

    # A Sleeper league whose only resolvable season(s) have not started yet
    # (pre_draft/drafting) yields no usable seasons — see sleeper_client. There is
    # nothing to fetch, process, or write. For ONBOARD this is a user error (the
    # league hasn't begun); for REFRESH/MIGRATE it is a no-op success (the league
    # keeps its existing data and the not-yet-started season is registered later,
    # once it flips to in_season).
    if not onboarding_service.client.get_seasons():
        league_id = body.get("leagueId")
        if request_type == "ONBOARD":
            logger.warning(
                "ONBOARD for league %s resolved no started seasons; nothing to onboard",
                league_id,
            )
            _record_failure(
                request_type,
                "NOT_STARTED",
                body,
                onboarding_service.canonical_league_id,
            )
            return {
                "statusCode": 400,
                "body": json.dumps(
                    {
                        "status": "failed",
                        "error_msg": "League has not started a season yet.",
                    }
                ),
            }
        logger.info(
            "%s for league %s resolved no started seasons; treating as no-op success",
            request_type,
            league_id,
        )
        write_job_status(
            correlation_id_var.get(),
            "COMPLETED",
            request_type,
            league_id=str(league_id) if league_id else None,
            platform=body.get("platform"),
            canonical_league_id=onboarding_service.canonical_league_id,
        )
        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "status": "succeeded",
                    "canonical_league_id": onboarding_service.canonical_league_id,
                }
            ),
        }

    try:
        onboarding_service.run()
    except KeyError as e:
        logger.error("Missing required environment variable: %s", e)
        _record_failure(
            request_type,
            "INTERNAL",
            body,
            onboarding_service.canonical_league_id,
            error_detail=str(e),
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
        _record_failure(
            request_type,
            classify_http_error(e),
            body,
            onboarding_service.canonical_league_id,
            error_detail=str(e),
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
        _record_failure(
            request_type,
            "UPSTREAM",
            body,
            onboarding_service.canonical_league_id,
            error_detail=str(e),
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
        _record_failure(
            request_type,
            "INTERNAL",
            body,
            onboarding_service.canonical_league_id,
            error_detail=str(e),
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
