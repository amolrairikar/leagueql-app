"""Shared JOB_STATUS item writes and failure classification for LeagueQL.

A ``JOB_STATUS`` item tracks the lifecycle of a single onboard/refresh/migrate
job so the frontend can poll it and surface a real failure reason. It is keyed by
``correlation_id`` (the only identifier known end-to-end at job-creation time,
even before a league lookup record exists), and carries a 24h TTL so old jobs
self-clean:

    PK = JOB#{correlation_id}
    SK = JOB_STATUS

The API creates the item (``IN_PROGRESS``) when it triggers a job; the onboarder
and processor amend it to ``FAILED``/``COMPLETED``. Writes are best-effort: a
JOB_STATUS write must never crash a Lambda or mask the underlying error, so
DynamoDB failures here are logged and swallowed.

Vendored into every function's deployment zip via the build script.
"""

import datetime
import os

import boto3
import botocore.config
import botocore.exceptions

from common.logging_utils import logger

_retry_config = botocore.config.Config(retries={"mode": "standard"})
_dynamodb = boto3.client("dynamodb", config=_retry_config)

# How long a JOB_STATUS item lives before DynamoDB TTL reaps it.
JOB_TTL_SECONDS = 24 * 60 * 60

# User-facing failure messages, keyed by failure_code. Raw exception detail is
# only ever logged / sent to SNS — never stored here — so credentials and stack
# traces are not exposed to end users. Messages may contain a ``{platform}``
# placeholder filled in by ``failure_reason()``.
FAILURE_REASONS: dict[str, str] = {
    "INVALID_INPUT": (
        "Some of the information provided was invalid. Please double-check your "
        "league ID and credentials, then try again."
    ),
    "ESPN_AUTH": (
        "ESPN rejected your credentials. Your espn_s2 / SWID cookies may have "
        "expired — re-copy them from ESPN and try again."
    ),
    "NOT_FOUND": (
        "We couldn't find that league on {platform}. Please confirm the league ID "
        "is correct."
    ),
    "UPSTREAM": (
        "We couldn't reach {platform} right now. Please try again in a few minutes."
    ),
    "PROCESSING": (
        "We hit a problem while building your league dashboard. Please try again, "
        "or contact support if it keeps happening."
    ),
    "INTERNAL": (
        "Something went wrong on our end. Please try again, or contact support if "
        "it keeps happening."
    ),
}

# Failure codes that indicate a systemic / our-fault problem worth an operational
# alert (SNS). The rest (INVALID_INPUT, ESPN_AUTH, NOT_FOUND) are expected user
# errors — recorded on the JOB_STATUS item so the user sees a reason, but never
# paged on, to keep the alert channel free of noise we can't act on.
SYSTEMIC_FAILURE_CODES = {"UPSTREAM", "PROCESSING", "INTERNAL"}

# How a platform value is rendered in user-facing messages.
PLATFORM_DISPLAY = {"ESPN": "ESPN", "SLEEPER": "Sleeper"}


def failure_reason(failure_code: str, platform: str | None = None) -> str:
    """
    Resolve a user-facing failure message, filling in the platform name.

    Args:
        failure_code: A key into FAILURE_REASONS (falls back to INTERNAL).
        platform: The platform value (e.g. "ESPN" / "SLEEPER"); when unknown the
            message reads "the fantasy platform".

    Returns:
        The resolved, user-facing failure message.
    """
    template = FAILURE_REASONS.get(failure_code, FAILURE_REASONS["INTERNAL"])
    platform_display = PLATFORM_DISPLAY.get(
        (platform or "").upper(), "the fantasy platform"
    )
    return template.format(platform=platform_display)


def job_status_key(correlation_id: str) -> dict[str, dict[str, str]]:
    """Return the DynamoDB key for a job's JOB_STATUS item."""
    return {"PK": {"S": f"JOB#{correlation_id}"}, "SK": {"S": "JOB_STATUS"}}


def classify_http_error(exc: Exception) -> str:
    """
    Map an HTTP-ish exception to a JOB_STATUS failure_code.

    A 401/403 means the user's credentials were rejected (commonly expired ESPN
    cookies); a 404 means the league genuinely does not exist on the platform
    (e.g. a mistyped league ID); anything else is treated as a transient upstream
    failure.

    Args:
        exc: The raised exception (e.g. requests.exceptions.HTTPError).

    Returns:
        "ESPN_AUTH" for auth failures, "NOT_FOUND" for 404s, otherwise "UPSTREAM".
    """
    response = getattr(exc, "response", None)
    status_code = getattr(response, "status_code", None)
    if status_code in (401, 403):
        return "ESPN_AUTH"
    if status_code == 404:
        return "NOT_FOUND"
    return "UPSTREAM"


def write_job_status(
    correlation_id: str,
    status: str,
    request_type: str | None = None,
    *,
    failure_code: str | None = None,
    league_id: str | None = None,
    platform: str | None = None,
    canonical_league_id: str | None = None,
) -> None:
    """
    Upsert a JOB_STATUS item for a job (best-effort; never raises).

    Uses an UpdateExpression so it amends the ``IN_PROGRESS`` item the API
    created, refreshing the TTL on every write. When ``failure_code`` is given,
    the matching user-facing message from ``FAILURE_REASONS`` is stored as
    ``failure_reason``. ``request_type`` is only overwritten when provided, so a
    terminal write that omits it preserves the value the creator set.

    Args:
        correlation_id: The job's correlation ID (its key). No-op if empty.
        status: "IN_PROGRESS" | "COMPLETED" | "FAILED".
        request_type: "ONBOARD" | "REFRESH" | "MIGRATE", or None to leave as-is.
        failure_code: A key into FAILURE_REASONS; only set on FAILED.
        league_id: The platform league ID (observability).
        platform: The platform, e.g. "ESPN" / "SLEEPER" (observability).
        canonical_league_id: The canonical league ID, when known (observability).
    """
    if not correlation_id:
        logger.warning("No correlation_id available; skipping JOB_STATUS write")
        return

    try:
        table_name = os.environ["DYNAMODB_TABLE_NAME"]
    except KeyError:
        logger.error("Environment variable 'DYNAMODB_TABLE_NAME' not set!")
        return

    now = datetime.datetime.now(datetime.timezone.utc)
    # "status" and "ttl" are both DynamoDB reserved words, so alias them.
    expr_names = {"#status": "status", "#ttl": "ttl"}
    expr_values = {
        ":status": {"S": status},
        ":updated_at": {"S": now.isoformat()},
        ":ttl": {"N": str(int(now.timestamp()) + JOB_TTL_SECONDS)},
    }
    set_parts = [
        "#status = :status",
        "updated_at = :updated_at",
        "#ttl = :ttl",
        "created_at = if_not_exists(created_at, :updated_at)",
    ]

    if request_type:
        expr_values[":request_type"] = {"S": request_type}
        set_parts.append("request_type = :request_type")

    if failure_code:
        expr_values[":failure_code"] = {"S": failure_code}
        expr_values[":failure_reason"] = {"S": failure_reason(failure_code, platform)}
        set_parts += [
            "failure_code = :failure_code",
            "failure_reason = :failure_reason",
        ]

    for attr_name, attr_value in (
        ("league_id", league_id),
        ("platform", platform),
        ("canonical_league_id", canonical_league_id),
    ):
        if attr_value:
            expr_values[f":{attr_name}"] = {"S": attr_value}
            set_parts.append(f"{attr_name} = :{attr_name}")

    try:
        _dynamodb.update_item(
            TableName=table_name,
            Key=job_status_key(correlation_id),
            UpdateExpression="SET " + ", ".join(set_parts),
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_values,
        )
        logger.info(
            "Wrote JOB_STATUS: correlation_id=%s status=%s request_type=%s failure_code=%s",
            correlation_id,
            status,
            request_type,
            failure_code,
        )
    except (botocore.exceptions.BotoCoreError, botocore.exceptions.ClientError) as e:
        # Best-effort: never let a status-tracking write mask the real error.
        # BotoCoreError covers credential/endpoint/connection failures too.
        logger.error(
            "Failed to write JOB_STATUS for correlation_id=%s: %s", correlation_id, e
        )
