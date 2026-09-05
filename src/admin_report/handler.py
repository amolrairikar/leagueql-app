"""Nightly onboarding-health report Lambda for LeagueQL.

Runs on an EventBridge schedule (08:00 UTC daily, prod-only), queries the GSI3
"all-leagues" index once (a single ``SK = "METADATA"`` query, paginated on
``LastEvaluatedKey``), and posts a formatted digest to the private LeagueQL Discord
channel via the same incoming webhook the infra/error alerts use. This replaces the
pull-based Streamlit admin dashboard (``scripts/admin_dashboard/``) with a push-based
nightly summary.

The digest reports total leagues onboarded, active leagues (accessed in the last 14
days), the ESPN-vs-SLEEPER split, and new onboards in the last 24h / 7d / 30d.

The webhook URL is a SecureString SSM parameter fetched at cold start by *name* (the
value never lands in a Lambda env var / TF state / CI), via ``common.secrets`` — the
same parameter and pattern as ``discord_notifier``. Like that Lambda, this one never
publishes failures back to the alert SNS topic (which would loop); on any failure it
logs and re-raises so the error surfaces in its own CloudWatch error metrics.
"""

import os
from datetime import datetime, timezone

import boto3
from aggregations import count_active, count_total, new_onboards, platform_counts
from boto3.dynamodb.conditions import Key

from common.http import build_retry_session
from common.logging_utils import logger
from common.secrets import get_secret_from_env_param

GSI3_INDEX_NAME = "GSI3"
ACTIVE_DAYS = 14

# Green "healthy digest" embed, distinct from the red alert embeds in discord_notifier.
_COLOR_GREEN = 0x2ECC71

_TABLE = boto3.resource("dynamodb").Table(os.environ["DYNAMODB_TABLE_NAME"])

# Webhook URL resolved once per cold start from its SSM parameter name.
_WEBHOOK_URL = get_secret_from_env_param("DISCORD_WEBHOOK_URL_SSM_PARAM")

_session = build_retry_session()


def _fetch_metadata_items() -> list[dict]:
    """Query GSI3 for every METADATA item, paginating on ``LastEvaluatedKey``."""
    items: list[dict] = []
    kwargs = {
        "IndexName": GSI3_INDEX_NAME,
        "KeyConditionExpression": Key("SK").eq("METADATA"),
    }
    while True:
        response = _TABLE.query(**kwargs)
        items.extend(response.get("Items", []))
        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            break
        kwargs["ExclusiveStartKey"] = last_key
    return items


def _build_embed(items: list[dict], now: datetime) -> dict:
    """Build the Discord embed summarizing onboarding health for ``items``."""
    total = count_total(items)
    active = count_active(items, now, days=ACTIVE_DAYS)
    platforms = platform_counts(items)
    recent = new_onboards(items, now)
    return {
        "title": "📊 LeagueQL nightly onboarding report",
        "color": _COLOR_GREEN,
        "fields": [
            {
                "name": "Total onboarded",
                "value": f"{total:,}",
                "inline": True,
            },
            {
                "name": f"Active ({ACTIVE_DAYS}d)",
                "value": f"{active:,}",
                "inline": True,
            },
            {
                "name": "ESPN / SLEEPER",
                "value": f"{platforms['ESPN']:,} / {platforms['SLEEPER']:,}",
                "inline": True,
            },
            {
                "name": "New onboards",
                "value": (
                    f"Last 24h: **{recent['24h']:,}**\n"
                    f"Last 7d: **{recent['7d']:,}**\n"
                    f"Last 30d: **{recent['30d']:,}**"
                ),
                "inline": False,
            },
        ],
        "footer": {"text": f"Generated {now:%Y-%m-%d %H:%M} UTC"},
    }


def _post_to_discord(embed: dict) -> None:
    """POST a single embed to the Discord webhook, raising on a non-2xx response."""
    response = _session.post(_WEBHOOK_URL, json={"embeds": [embed]}, timeout=5)
    response.raise_for_status()


def lambda_handler(event, context) -> None:
    """Scheduled entry point: aggregate onboarding health and post the digest.

    Any failure (unset webhook, DynamoDB query error, non-2xx Discord response) is
    logged and re-raised so it shows up in this Lambda's CloudWatch error metrics; it
    is intentionally *not* republished to the alert SNS topic, which would loop.
    """
    if not _WEBHOOK_URL:
        logger.error("DISCORD_WEBHOOK_URL_SSM_PARAM unset; cannot post report")
        raise RuntimeError("Discord webhook URL is not configured")

    try:
        items = _fetch_metadata_items()
        now = datetime.now(timezone.utc)
        embed = _build_embed(items, now)
        _post_to_discord(embed)
    except Exception:
        logger.exception("Failed to generate or post the nightly onboarding report")
        raise

    logger.info("Posted nightly onboarding report for %d leagues", len(items))
