"""Shared subscription-state writes for LeagueQL (BE-015).

The Stripe billing webhook is the **single writer** of ``subscription_end_time`` on
a league's ``METADATA`` item; the API layer only *reads* it (BE-014
``require_active_subscription``). This module holds the conditional DynamoDB writes
that back that behavior. It uses its own ``boto3`` client (mirroring
``common.job_status``) so it can be vendored into both the API and ``stripe_webhook``
Lambda deployment zips.

Writes are conditional so they are safe under Stripe's at-least-once, possibly
out-of-order webhook delivery:

* ``record_active_subscription`` advances ``subscription_end_time`` **monotonically**
  and claims ``stripe_subscription_id`` for the league. A *different* subscription
  already recorded for the league surfaces as ``DuplicateSubscription`` so the caller
  can cancel the duplicate (reconciliation). The ``pending_checkout`` marker is
  cleared on a successful write.
* ``expire_subscription`` drives access to expired on cancellation / terminal
  failure, scoped to the recorded subscription so a duplicate's deletion cannot
  revoke the surviving subscription.

See ``docs/requirements/backend/BE-015-stripe-billing.md`` (Idempotency Layer 3).
"""

import os

import boto3
import botocore.config

from common.logging_utils import logger

_retry_config = botocore.config.Config(retries={"mode": "standard"})
_dynamodb = boto3.client("dynamodb", config=_retry_config)

# Far-past timestamp written to mark a subscription expired (BE-014 treats any
# ``subscription_end_time <= now`` as expired).
EXPIRED_AT = "1970-01-01T00:00:00+00:00"


class DuplicateSubscription(Exception):
    """A *different* active subscription is already recorded for the league.

    Raised by ``record_active_subscription`` so the caller can reconcile by
    canceling the duplicate (the subscription it was trying to record).
    """


def _metadata_key(canonical_league_id: str) -> dict[str, dict[str, str]]:
    return {
        "PK": {"S": f"LEAGUE#{canonical_league_id}"},
        "SK": {"S": "METADATA"},
    }


def _recorded_subscription_id(table_name: str, canonical_league_id: str) -> str | None:
    """Return the ``stripe_subscription_id`` currently stored on the league, if any."""
    resp = _dynamodb.get_item(
        TableName=table_name,
        Key=_metadata_key(canonical_league_id),
        ProjectionExpression="stripe_subscription_id",
    )
    return resp.get("Item", {}).get("stripe_subscription_id", {}).get("S")


def record_active_subscription(
    canonical_league_id: str,
    subscription_end_time: str,
    stripe_subscription_id: str,
    *,
    mark_trial_used: bool = False,
) -> bool:
    """Monotonically record an active/trialing subscription's end time.

    Performs a single conditional ``UpdateItem`` that (a) only advances
    ``subscription_end_time`` (never regresses on a stale/out-of-order event),
    (b) claims ``stripe_subscription_id`` for the league, and (c) clears any
    ``pending_checkout`` marker. When ``mark_trial_used`` is set, ``trial_used``
    is recorded so the league never receives a second trial (BE-015: trial once).

    Args:
        canonical_league_id: The canonical league ID.
        subscription_end_time: ISO 8601 (UTC) ``trial_end`` (trialing) or
            ``current_period_end`` (active).
        stripe_subscription_id: The Stripe subscription this state came from.
        mark_trial_used: Set ``trial_used`` on the league (when recording a
            trialing subscription).

    Returns:
        ``True`` when the write applied; ``False`` when it was a no-op (the stored
        end time was already >= the new one — a stale or duplicate event).

    Raises:
        DuplicateSubscription: A *different* ``stripe_subscription_id`` is already
            recorded for the league.
    """
    table_name = os.environ["DYNAMODB_TABLE_NAME"]
    set_parts = ["subscription_end_time = :t", "stripe_subscription_id = :sid"]
    values = {
        ":t": {"S": subscription_end_time},
        ":sid": {"S": stripe_subscription_id},
    }
    if mark_trial_used:
        set_parts.append("trial_used = :tu")
        values[":tu"] = {"BOOL": True}

    try:
        _dynamodb.update_item(
            TableName=table_name,
            Key=_metadata_key(canonical_league_id),
            UpdateExpression="SET " + ", ".join(set_parts) + " REMOVE pending_checkout",
            ConditionExpression=(
                "attribute_exists(PK) "
                "AND (attribute_not_exists(stripe_subscription_id) "
                "OR stripe_subscription_id = :sid) "
                "AND (attribute_not_exists(subscription_end_time) "
                "OR subscription_end_time < :t)"
            ),
            ExpressionAttributeValues=values,
        )
        logger.info(
            "Recorded active subscription: league=%s sub=%s end=%s",
            canonical_league_id,
            stripe_subscription_id,
            subscription_end_time,
        )
        return True
    except _dynamodb.exceptions.ConditionalCheckFailedException:
        # The condition guards three things at once. Re-read to tell a genuine
        # duplicate (a *different* subscription already recorded) apart from a
        # harmless non-advancing write (stale/duplicate event, or missing league).
        recorded = _recorded_subscription_id(table_name, canonical_league_id)
        if recorded is not None and recorded != stripe_subscription_id:
            raise DuplicateSubscription(
                f"League {canonical_league_id} already has subscription {recorded}; "
                f"{stripe_subscription_id} is a duplicate"
            )
        logger.info(
            "No-op subscription write for league=%s sub=%s (non-advancing)",
            canonical_league_id,
            stripe_subscription_id,
        )
        return False


def expire_subscription(canonical_league_id: str, stripe_subscription_id: str) -> bool:
    """Drive a league's access to expired on cancellation / terminal failure.

    Sets ``subscription_end_time`` to the far past and clears ``pending_checkout``,
    **scoped to the recorded subscription** so canceling a duplicate cannot revoke
    the surviving subscription's access.

    Args:
        canonical_league_id: The canonical league ID.
        stripe_subscription_id: The subscription being canceled/terminated; the
            write only applies when this is the league's recorded subscription.

    Returns:
        ``True`` when access was expired; ``False`` when the subscription was not
        the recorded one (e.g. a duplicate being canceled) so nothing changed.
    """
    table_name = os.environ["DYNAMODB_TABLE_NAME"]
    try:
        _dynamodb.update_item(
            TableName=table_name,
            Key=_metadata_key(canonical_league_id),
            UpdateExpression="SET subscription_end_time = :past REMOVE pending_checkout",
            ConditionExpression=(
                "attribute_exists(PK) AND stripe_subscription_id = :sid"
            ),
            ExpressionAttributeValues={
                ":past": {"S": EXPIRED_AT},
                ":sid": {"S": stripe_subscription_id},
            },
        )
        logger.info(
            "Expired subscription: league=%s sub=%s",
            canonical_league_id,
            stripe_subscription_id,
        )
        return True
    except _dynamodb.exceptions.ConditionalCheckFailedException:
        logger.info(
            "Skipped expire for league=%s sub=%s (not the recorded subscription)",
            canonical_league_id,
            stripe_subscription_id,
        )
        return False
