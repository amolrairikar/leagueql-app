"""Shared onboarder-Lambda invocation for LeagueQL services.

Vendored into every function's deployment zip. Centralizes the async invoke
payload contract (``body`` / ``requestType`` / ``canonicalLeagueId`` /
``correlation_id``) shared by the API and the Sleeper refresh job.
"""

import json
from typing import Any


def invoke_onboarder(
    lambda_client: Any,
    function_name: str,
    body: dict,
    request_type: str,
    canonical_league_id: str | None,
    correlation_id: str,
    owner_user_id: str | None = None,
) -> dict:
    """
    Asynchronously invoke the onboarder Lambda with the standard payload contract.

    Args:
        lambda_client: A boto3 Lambda client.
        function_name: The onboarder Lambda's function name.
        body: The onboarder request body (leagueId/platform/cookies/season/etc.).
        request_type: One of ONBOARD, REFRESH, or MIGRATE.
        canonical_league_id: The canonical league ID, or None for first-time onboarding.
        correlation_id: Correlation ID propagated for request tracing.
        owner_user_id: Clerk user ID of the onboarding owner, recorded on the
            league's METADATA on first ONBOARD (LQL-01 / BE-016). ``None`` for the
            Sleeper auto-refresh job and other system-initiated invocations.

    Returns:
        The boto3 ``invoke`` response.
    """
    payload = {
        "body": body,
        "requestType": request_type,
        "canonicalLeagueId": canonical_league_id,
        "correlation_id": correlation_id,
        "ownerUserId": owner_user_id,
    }
    return lambda_client.invoke(
        FunctionName=function_name,
        InvocationType="Event",
        Payload=json.dumps(payload),
    )
