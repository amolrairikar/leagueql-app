"""Shared pending-recap enqueue for LeagueQL (BE-022).

Vendored into the processor + Stripe-webhook deployment zips. Replaces the old
``ecs:RunTask`` launcher: instead of starting generation compute, the triggers record
a lightweight **pending-work marker** in DynamoDB. The recap-drainer Lambda later
aggregates every pending league's missing weeks into one Bedrock batch job.

The marker is **one item per league** (``PK=RECAP_QUEUE``, ``SK=PENDING#{league}``),
written with a conditional put that will **not clobber an ``in_flight`` marker** — a
league already mid-job stays mid-job and its newly-completed weeks are picked up on
the next enqueue after that job finishes. A re-trigger of a ``pending`` league simply
refreshes the marker, so the queue never duplicates.

No-op when billing is disabled or in the non-east region (``RECAP_QUEUE_TABLE``
unset). A failed put is swallowed so enqueue never fails the webhook or the processor.
"""

import datetime
import json
import os

import boto3
from botocore.exceptions import ClientError

from common.feature_flags import is_billing_enabled
from common.logging_utils import logger
from common.tracing import inject_context

_dynamodb = boto3.resource("dynamodb")


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def record_pending_recap(
    *,
    canonical_league_id: str,
    platform: str | None = None,
    correlation_id: str = "",
    native_league_id: str | None = None,
) -> None:
    """Record that a league needs a recap pass (fire-and-forget).

    No-ops when ``RECAP_QUEUE_TABLE`` is unset (non-east region) or billing is off.
    The conditional put leaves an ``in_flight`` marker untouched; any other failure is
    logged and swallowed so the caller (a processor run or the webhook) never fails.
    """
    table_name = os.environ.get("RECAP_QUEUE_TABLE")
    if not table_name:
        logger.info("Recap queue not configured; skipping recap enqueue")
        return
    if not is_billing_enabled():
        logger.info("Billing disabled; skipping recap enqueue")
        return

    item = {
        "PK": "RECAP_QUEUE",
        "SK": f"PENDING#{canonical_league_id}",
        "canonical_league_id": canonical_league_id,
        "status": "pending",
        "correlation_id": correlation_id or "",
        "trace_context": json.dumps(inject_context({})),
        "enqueued_at": _now_iso(),
    }
    if platform:
        item["platform"] = platform
    if native_league_id:
        item["native_league_id"] = native_league_id

    try:
        _dynamodb.Table(table_name).put_item(
            Item=item,
            ConditionExpression="attribute_not_exists(SK) OR #s <> :inflight",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":inflight": "in_flight"},
        )
        logger.info("Enqueued pending recap for league=%s", canonical_league_id)
    except ClientError as exc:
        if (
            exc.response.get("Error", {}).get("Code")
            == "ConditionalCheckFailedException"
        ):
            logger.info(
                "League %s already has a recap job in flight; skipping enqueue",
                canonical_league_id,
            )
            return
        logger.error("Failed to enqueue pending recap: %s", exc)
    except Exception as exc:
        logger.error("Failed to enqueue pending recap: %s", exc)
