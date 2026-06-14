"""SNS-to-Discord alert forwarder Lambda for LeagueQL.

Subscribes to the ``leagueql-lambda-alerts-prod-<region>`` SNS topic and forwards
every alert to a private Discord channel via an incoming webhook. The SNS topic is
the hub for all infra/error alerts — CloudWatch alarms, the Fargate (Sleeper stats)
task-failure EventBridge rule, and app-level ``common.sns.publish_failure`` calls
from the onboarder/processor/API Lambdas — so this single subscriber replaces the
former email subscription.

A Lambda is required because Discord webhooks accept only a specific JSON body and
cannot complete SNS's HTTPS subscription confirmation handshake, so SNS cannot POST
to Discord directly.

The webhook URL is a SecureString SSM parameter fetched at cold start by *name*
(the value never lands in a Lambda env var / TF state / CI), mirroring the Stripe
secret pattern in ``common.secrets``. This Lambda deliberately never calls
``publish_failure`` (that republishes to the same topic → loop); on failure it logs
and re-raises so the error surfaces in its own CloudWatch metrics.
"""

import json

from common.http import build_retry_session
from common.logging_utils import logger
from common.secrets import get_secret_from_env_param

# Discord embed colors (decimal RGB).
_COLOR_RED = 0xE74C3C  # ALARM / failures
_COLOR_GREEN = 0x2ECC71  # OK / recovery
_COLOR_GREY = 0x95A5A6  # informational / unknown shape

# Discord payload limits (with headroom). See
# https://discord.com/developers/docs/resources/webhook.
_TITLE_LIMIT = 256
_DESCRIPTION_LIMIT = 4096
_FIELD_VALUE_LIMIT = 1024

# Webhook URL resolved once per cold start from its SSM parameter name.
_WEBHOOK_URL = get_secret_from_env_param("DISCORD_WEBHOOK_URL_SSM_PARAM")

_session = build_retry_session()


def _truncate(text: str, limit: int) -> str:
    """Trim ``text`` to ``limit`` characters, marking truncation with an ellipsis."""
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def _alarm_embed(message: dict) -> dict:
    """Build a Discord embed from a CloudWatch alarm notification."""
    state = message.get("NewStateValue", "UNKNOWN")
    color = _COLOR_GREEN if state == "OK" else _COLOR_RED
    fields = [{"name": "State", "value": state, "inline": True}]
    region = message.get("Region")
    if region:
        fields.append({"name": "Region", "value": region, "inline": True})
    reason = message.get("NewStateReason") or message.get("AlarmDescription") or ""
    return {
        "title": _truncate(message.get("AlarmName", "CloudWatch Alarm"), _TITLE_LIMIT),
        "description": _truncate(reason, _DESCRIPTION_LIMIT),
        "color": color,
        "fields": fields,
    }


def _eventbridge_embed(message: dict) -> dict:
    """Build a Discord embed from an EventBridge event (e.g. Fargate task failure)."""
    detail_type = message.get("detail-type", "EventBridge Event")
    detail = json.dumps(message.get("detail", {}), indent=2, default=str)
    return {
        "title": _truncate(detail_type, _TITLE_LIMIT),
        "description": _truncate(f"```json\n{detail}\n```", _DESCRIPTION_LIMIT),
        "color": _COLOR_RED,
    }


def _plain_embed(subject: str | None, body: str) -> dict:
    """Build a Discord embed from a plain-text alert (app ``publish_failure``)."""
    return {
        "title": _truncate(subject or "LeagueQL Alert", _TITLE_LIMIT),
        "description": _truncate(body, _DESCRIPTION_LIMIT),
        "color": _COLOR_RED,
    }


def _embed_for_record(subject: str | None, body: str) -> dict:
    """Map an SNS record's subject/body to a Discord embed, tolerating any shape.

    CloudWatch alarms and the EventBridge rule deliver JSON in the SNS message;
    app-level ``publish_failure`` delivers plain text. Parsing is defensive so an
    unexpected payload still forwards as plain text rather than dropping the alert.
    """
    try:
        parsed = json.loads(body)
    except (ValueError, TypeError):
        return _plain_embed(subject, body)

    if not isinstance(parsed, dict):
        return _plain_embed(subject, body)
    if "AlarmName" in parsed and "NewStateValue" in parsed:
        return _alarm_embed(parsed)
    if "detail-type" in parsed and "source" in parsed:
        return _eventbridge_embed(parsed)
    # Some other JSON object — forward it pretty-printed so nothing is lost.
    return _plain_embed(subject, json.dumps(parsed, indent=2, default=str))


def _post_to_discord(embed: dict) -> None:
    """POST a single embed to the Discord webhook, raising on a non-2xx response."""
    response = _session.post(_WEBHOOK_URL, json={"embeds": [embed]}, timeout=5)
    response.raise_for_status()


def lambda_handler(event, context) -> None:
    """SNS entry point: forward every record in the event to Discord.

    Each ``Records[].Sns`` entry becomes one Discord embed. Any delivery failure is
    logged and re-raised so it shows up in this Lambda's CloudWatch error metrics
    (it is intentionally *not* republished to SNS, which would loop).
    """
    if not _WEBHOOK_URL:
        logger.error("DISCORD_WEBHOOK_URL_SSM_PARAM unset; cannot forward alert")
        raise RuntimeError("Discord webhook URL is not configured")

    for record in event.get("Records", []):
        sns = record.get("Sns", {})
        embed = _embed_for_record(sns.get("Subject"), sns.get("Message", ""))
        try:
            _post_to_discord(embed)
        except Exception:
            logger.exception("Failed to forward SNS alert to Discord")
            raise
