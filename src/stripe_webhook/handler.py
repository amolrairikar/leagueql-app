"""Stripe billing webhook Lambda for LeagueQL (BE-015).

Receives Stripe webhook events behind API Gateway, verifies the signature, and
converges each league's subscription state. This Lambda is the **single writer**
of ``subscription_end_time`` (via ``common.subscription``).

Idempotency is enforced in three layers (see
``docs/requirements/backend/BE-015-stripe-billing.md``):

* **Signature verification** rejects forged / misconfigured payloads (``400``).
* A ``WEBHOOK_EVENT#{event_id}`` dedup item makes processing exactly-once under
  Stripe's at-least-once delivery — checked first, recorded **only after** the
  event is processed successfully so a mid-processing failure is safely retried.
* The conditional DynamoDB writes in ``common.subscription`` converge state
  regardless of event ordering and surface duplicate subscriptions so this Lambda
  can reconcile by canceling the extra one.
"""

import base64
import datetime
import json
import os

import boto3
import botocore.config
import stripe

from common.logging_utils import logger
from common.secrets import get_secret_from_env_param
from common.subscription import (
    DuplicateSubscription,
    expire_subscription,
    record_active_subscription,
)

# Stripe credentials are SecureString SSM parameters fetched at cold start by
# parameter *name* (the value never lands in a Lambda env var / TF state / CI).
# See docs/requirements/backend/BE-015-stripe-billing.md.
stripe.api_key = get_secret_from_env_param("STRIPE_SECRET_KEY_SSM_PARAM")
_WEBHOOK_SECRET = get_secret_from_env_param("STRIPE_WEBHOOK_SECRET_SSM_PARAM")

_retry_config = botocore.config.Config(retries={"mode": "standard"})
_dynamodb = boto3.client("dynamodb", config=_retry_config)

# Event types that record/refresh an active or trialing subscription.
_ACTIVATING_EVENTS = {
    "checkout.session.completed",
    "customer.subscription.created",
    "customer.subscription.updated",
    "invoice.paid",
}

# Subscription statuses that revoke access (terminal / unrecoverable).
_TERMINAL_STATUSES = {"canceled", "unpaid", "incomplete_expired"}

# How long a processed-event dedup marker lives before DynamoDB TTL reaps it.
WEBHOOK_EVENT_TTL_SECONDS = 7 * 24 * 60 * 60


def _response(status_code: int, message: str) -> dict[str, str | int]:
    return {"statusCode": status_code, "body": json.dumps({"detail": message})}


def _raw_body(event: dict) -> bytes | str:
    """Return the raw (undecoded) request body needed for signature verification."""
    body = event.get("body") or ""
    if event.get("isBase64Encoded"):
        return base64.b64decode(body)
    return body


def _signature_header(event: dict) -> str | None:
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    return headers.get("stripe-signature")


def _webhook_event_key(event_id: str) -> dict[str, dict[str, str]]:
    return {
        "PK": {"S": f"WEBHOOK_EVENT#{event_id}"},
        "SK": {"S": "WEBHOOK_EVENT"},
    }


def _event_already_processed(event_id: str) -> bool:
    resp = _dynamodb.get_item(
        TableName=os.environ["DYNAMODB_TABLE_NAME"],
        Key=_webhook_event_key(event_id),
    )
    return "Item" in resp


def _record_event_processed(event_id: str) -> None:
    now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    item = _webhook_event_key(event_id)
    item["ttl"] = {"N": str(now + WEBHOOK_EVENT_TTL_SECONDS)}
    _dynamodb.put_item(
        TableName=os.environ["DYNAMODB_TABLE_NAME"],
        Item=item,
    )


def _iso(unix_ts: int) -> str:
    return datetime.datetime.fromtimestamp(
        unix_ts, tz=datetime.timezone.utc
    ).isoformat()


def _get(obj, key, default=None):
    """Safe key access for Stripe objects and plain dicts.

    stripe-python (v15) resource objects are **not** ``dict`` subclasses and have
    no ``.get()`` — they support ``obj[key]`` (raising ``KeyError`` when missing).
    Plain dicts (used in tests) behave the same way, so subscript-with-fallback
    works for both. Using ``.get()`` directly on a real Stripe object raises
    ``AttributeError: get``.
    """
    try:
        return obj[key]
    except (KeyError, TypeError):
        return default


def _current_period_end(subscription) -> int | None:
    """Return ``current_period_end``, tolerating its move to the item level."""
    end = _get(subscription, "current_period_end")
    if end:
        return end
    items = _get(_get(subscription, "items") or {}, "data") or []
    if items and _get(items[0], "current_period_end"):
        return _get(items[0], "current_period_end")
    return None


def _subscription_end_time(subscription) -> str | None:
    """Map a subscription to its access-end timestamp (trial vs. paid period)."""
    if _get(subscription, "status") == "trialing" and _get(subscription, "trial_end"):
        return _iso(_get(subscription, "trial_end"))
    period_end = _current_period_end(subscription)
    return _iso(period_end) if period_end else None


def _subscription_id_from_event(event_type: str, obj) -> str | None:
    if event_type in (
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
    ):
        return _get(obj, "id")
    # ``checkout.session.completed`` and ``invoice.paid`` reference the subscription.
    return _get(obj, "subscription")


def _process_event(stripe_event: dict) -> None:
    """Apply a verified Stripe event to the league's subscription state."""
    event_type = stripe_event["type"]
    obj = stripe_event["data"]["object"]

    # ``deleted`` carries the (now-canceled) subscription object directly; there
    # is nothing to re-fetch, so expire access scoped to that subscription.
    if event_type == "customer.subscription.deleted":
        canonical_league_id = _get(_get(obj, "metadata") or {}, "canonical_league_id")
        if not canonical_league_id:
            logger.warning("subscription.deleted without canonical_league_id; skipping")
            return
        expire_subscription(canonical_league_id, _get(obj, "id"))
        return

    if event_type not in _ACTIVATING_EVENTS:
        logger.info("Ignoring unhandled Stripe event type %s", event_type)
        return

    subscription_id = _subscription_id_from_event(event_type, obj)
    if not subscription_id:
        logger.info("Event %s has no subscription reference; skipping", event_type)
        return

    # Convergence: act on the subscription's authoritative current state rather
    # than the (possibly stale / out-of-order) event payload.
    subscription = stripe.Subscription.retrieve(subscription_id)
    sub_metadata = _get(subscription, "metadata") or {}
    canonical_league_id = _get(sub_metadata, "canonical_league_id")
    if not canonical_league_id:
        logger.warning(
            "Subscription %s missing canonical_league_id; skipping", subscription_id
        )
        return
    # Native identity (carried in the subscription metadata at checkout) keys the
    # durable, delete-surviving trial marker (BE-015).
    native_platform = _get(sub_metadata, "platform")
    native_league_id = _get(sub_metadata, "native_league_id")

    sub_status = _get(subscription, "status")
    if sub_status in ("active", "trialing"):
        end_time = _subscription_end_time(subscription)
        if not end_time:
            logger.warning("Subscription %s has no end time; skipping", subscription_id)
            return
        try:
            record_active_subscription(
                canonical_league_id,
                end_time,
                subscription_id,
                mark_trial_used=(sub_status == "trialing"),
                platform=native_platform,
                native_league_id=native_league_id,
            )
        except DuplicateSubscription:
            # A different subscription is already recorded for this league; this
            # one is the duplicate, so cancel it (Layer 3 reconciliation).
            logger.warning(
                "Canceling duplicate subscription %s for league %s",
                subscription_id,
                canonical_league_id,
            )
            stripe.Subscription.cancel(subscription_id)
    elif sub_status in _TERMINAL_STATUSES:
        expire_subscription(canonical_league_id, subscription_id)
    else:
        logger.info(
            "Subscription %s in status %s; no state change",
            subscription_id,
            sub_status,
        )


def lambda_handler(event, context) -> dict[str, str | int]:
    """API Gateway entry point for Stripe webhook delivery.

    Verifies the signature, dedups on the Stripe event id, processes the event,
    and only then records the dedup marker. A processing failure returns ``500``
    without recording, so Stripe redelivers and the (idempotent) handler retries.
    """
    payload = _raw_body(event)
    signature = _signature_header(event)

    try:
        stripe_event = stripe.Webhook.construct_event(
            payload, signature, _WEBHOOK_SECRET
        )
    except Exception as exc:
        # ``construct_event`` raises ValueError (bad payload) or
        # SignatureVerificationError (bad/mismatched signature, incl. a
        # test-vs-live mode mismatch). Either way, reject without state change.
        logger.warning("Stripe webhook signature verification failed: %s", exc)
        return _response(400, "Invalid signature")

    event_id = stripe_event["id"]
    if _event_already_processed(event_id):
        logger.info("Webhook event %s already processed; skipping", event_id)
        return _response(200, "Already processed")

    try:
        _process_event(stripe_event)
    except Exception as exc:
        # Do not record the dedup marker: returning 500 lets Stripe redeliver,
        # and Layer-3 convergence makes reprocessing safe.
        logger.exception("Failed to process webhook %s: %s", event_id, exc)
        return _response(500, "Processing error")

    _record_event_processed(event_id)
    return _response(200, "OK")
