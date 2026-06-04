"""Helper functions for the LeagueQL API.

DynamoDB access, Sleeper NFL state, SNS alerting, and small data utilities.
Functions that touch the patched singleton ``table`` reach it through the ``main``
module at call time so tests can patch ``main.table`` and have it take effect here.
SNS failure alerting lives in the shared ``common.sns`` module.
"""

import time
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from functools import partial
from typing import Any

import botocore.exceptions
import requests as http_requests
import stripe
from boto3.dynamodb.conditions import Key
from fastapi import HTTPException, status

import main
from common.job_status import JOB_TTL_SECONDS
from common.sns import publish_failure as _publish_failure
from main import (
    SLEEPER_STATE_URL,
    logger,
)

# Binds the API's SNS subject; the shared implementation handles the no-op guard,
# correlation_id, and error swallowing.
publish_failure = partial(_publish_failure, subject="LeagueQL API Failure")


def convert_decimals(obj: Any) -> Any:
    """Recursively convert Decimal values to float for JSON serialization."""
    if isinstance(obj, list):
        return [convert_decimals(i) for i in obj]
    if isinstance(obj, dict):
        return {k: convert_decimals(v) for k, v in obj.items()}
    if isinstance(obj, Decimal):
        return float(obj)
    return obj


def lookup_league(league_id: str, platform) -> str:
    """
    Utility function to lookup a given league.

    Args:
        league_id: The ID for the league.
        platform: The platform the league is on (e.g., ESPN, SLEEPER).

    Returns:
        The canonical league ID associated with that league.
    """
    pk = f"LEAGUE#{league_id}#PLATFORM#{platform.value}"
    sk = "LEAGUE_LOOKUP"
    try:
        response = main.table.get_item(Key={"PK": pk, "SK": sk})
    except botocore.exceptions.ClientError as e:
        logger.error("Boto error occurred: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to look up league",
        )

    item = response.get("Item")
    if not item:
        logger.warning("League %s not found for %s platform", league_id, platform.value)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="League not found",
        )

    if not item.get("canonical_league_id"):
        logger.error(
            "canonical_league_id not found in item for league %s on platform %s",
            league_id,
            platform.value,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )

    return item["canonical_league_id"]


def get_league_metadata(canonical_league_id: str) -> dict:
    """
    Utility function to get league metadata for a given canonical league ID.

    Args:
        canonical_league_id: The canonical league ID.

    Returns:
        A dictionary containing the league metadata.
    """
    pk = f"LEAGUE#{canonical_league_id}"
    sk = "METADATA"
    try:
        response = main.table.get_item(Key={"PK": pk, "SK": sk})
    except botocore.exceptions.ClientError as e:
        logger.error("Boto error occurred: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve league data",
        )

    item = response.get("Item")
    if not item:
        logger.warning("League with canonical ID %s not found", canonical_league_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )

    return item


def get_nfl_state() -> dict | None:
    """
    Fetches the current NFL state from Sleeper.

    Returns:
        The NFL state response (containing season_type, season, and week),
        or None if the request fails (fail-open so refresh stays available).
    """
    try:
        resp = http_requests.get(SLEEPER_STATE_URL, timeout=(5, 10))
        resp.raise_for_status()
        return resp.json()
    except Exception:
        logger.warning(
            "Failed to fetch NFL state; skipping refresh guard", exc_info=True
        )
        return None


def get_latest_stored_matchup(canonical_league_id: str) -> tuple[int, int] | None:
    """
    Finds the most recent stored matchup for a league.

    Matchups are keyed SK=MATCHUPS#{season}#WEEK#{week:02d}. Because season is
    4-digit and week is zero-padded, the lexicographically-largest MATCHUPS# SK
    is the latest stored season/week.

    Args:
        canonical_league_id: The canonical league ID.

    Returns:
        A (season, week) tuple for the most recent stored matchup, or None if
        the league has no matchups stored.
    """
    try:
        response = main.table.query(
            KeyConditionExpression=Key("PK").eq(f"LEAGUE#{canonical_league_id}")
            & Key("SK").begins_with("MATCHUPS#"),
            ScanIndexForward=False,
            Limit=1,
            ProjectionExpression="SK",
        )
    except botocore.exceptions.ClientError as e:
        logger.error("Boto error occurred: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve league data",
        )

    items = response.get("Items", [])
    if not items:
        return None
    # SK format: MATCHUPS#{season}#WEEK#{week}
    _, season, _, week = items[0]["SK"].split("#")
    return int(season), int(week)


def get_league_seasons(canonical_league_id: str) -> list[str]:
    """
    Uses GSI1 to find all seasons a league has been onboarded for.

    Queries all LEAGUE_LOOKUP items that share the given canonical_league_id
    (there may be multiple for Sleeper leagues) and merges their season sets.

    Args:
        canonical_league_id: The canonical league ID to look up.

    Returns:
        A sorted list of unique season strings (e.g. ["2022", "2023", "2025"]).
    """
    try:
        response = main.table.query(
            IndexName="GSI1",
            KeyConditionExpression=Key("canonical_league_id").eq(canonical_league_id),
        )
    except botocore.exceptions.ClientError as e:
        logger.error("Boto error occurred: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve league seasons",
        )

    items = response.get("Items", [])
    if not items:
        logger.warning(
            "No LEAGUE_LOOKUP items found for canonical_league_id %s",
            canonical_league_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )

    seasons: set[str] = set()
    for item in items:
        seasons.update(item.get("seasons", set()))

    return sorted(seasons)


def _query_all_keys(query_kwargs: dict) -> list[dict]:
    """
    Run a paginated query, returning every matched item's {PK, SK} key.

    Args:
        query_kwargs: Keyword arguments passed to table.query (must project PK/SK).

    Returns:
        A list of {"PK", "SK"} key dicts across all result pages.
    """
    keys: list[dict] = []
    kwargs = dict(query_kwargs)
    while True:
        response = main.table.query(**kwargs)
        for item in response.get("Items", []):
            keys.append({"PK": item["PK"], "SK": item["SK"]})
        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            return keys
        kwargs["ExclusiveStartKey"] = last_key


def collect_league_keys(canonical_league_id: str) -> list[dict]:
    """
    Collect the keys of every DynamoDB item belonging to a league.

    This covers two key spaces:
      * everything under the canonical PK (METADATA and all precomputed views,
        including any future SK types) read with strong consistency, and
      * the LEAGUE_LOOKUP items, which live under their own per-platform PKs and
        are located via GSI1 (eventually consistent).

    Args:
        canonical_league_id: The canonical league ID.

    Returns:
        A list of {"PK", "SK"} key dicts for every item owned by the league.
    """
    keys = _query_all_keys(
        {
            "KeyConditionExpression": Key("PK").eq(f"LEAGUE#{canonical_league_id}"),
            "ProjectionExpression": "PK, SK",
            "ConsistentRead": True,
        }
    )
    keys += _query_all_keys(
        {
            "IndexName": "GSI1",
            "KeyConditionExpression": Key("canonical_league_id").eq(
                canonical_league_id
            ),
            "ProjectionExpression": "PK, SK",
        }
    )
    return keys


def delete_all_league_items(canonical_league_id: str, max_attempts: int = 4) -> None:
    """
    Delete every DynamoDB item for a league, retrying until none remain.

    Rather than deleting a hardcoded set of SK prefixes, this discovers the
    league's actual items on each pass and deletes them, then re-verifies. This
    catches orphaned items (e.g. PLATFORM_MIGRATION#) regardless of SK type and
    tolerates GSI1 eventual-consistency lag on LEAGUE_LOOKUP items.

    Args:
        canonical_league_id: The canonical league ID.
        max_attempts: Number of delete+verify passes before giving up.

    Raises:
        HTTPException: 500 if items still remain after max_attempts.
    """
    for attempt in range(1, max_attempts + 1):
        keys = collect_league_keys(canonical_league_id)
        if not keys:
            return
        logger.info(
            "Delete attempt %d/%d: removing %d items for %s",
            attempt,
            max_attempts,
            len(keys),
            canonical_league_id,
        )
        with main.table.batch_writer() as writer:
            for key in keys:
                writer.delete_item(Key=key)
        time.sleep(0.5 * attempt)  # let GSI1 catch up before re-verifying

    remaining = collect_league_keys(canonical_league_id)
    if remaining:
        remaining_sks = [key["SK"] for key in remaining]
        logger.error(
            "Orphaned items remain for %s after %d attempts: %s",
            canonical_league_id,
            max_attempts,
            remaining_sks,
        )
        publish_failure(
            f"Orphaned items remain for league {canonical_league_id} after "
            f"{max_attempts} delete attempts: {remaining_sks}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fully delete league data",
        )


def create_job_status(
    correlation_id: str,
    request_type: str,
    league_id: str | None = None,
    platform: str | None = None,
    canonical_league_id: str | None = None,
) -> None:
    """
    Create the initial IN_PROGRESS JOB_STATUS item for a triggered job.

    Keyed by correlation_id so it is reachable by the frontend even when no
    league lookup record exists yet (e.g. a brand-new onboard). The onboarder /
    processor later upsert this same item to FAILED / COMPLETED. Best-effort: a
    failure here is logged but does not block triggering the job (the onboarder
    upserts the item regardless).

    Args:
        correlation_id: The job's correlation ID (its key).
        request_type: "ONBOARD" | "REFRESH" | "MIGRATE".
        league_id: The platform league ID (observability).
        platform: The platform, e.g. "ESPN" / "SLEEPER" (observability).
        canonical_league_id: The canonical league ID, when known (observability).
    """
    now = datetime.now(timezone.utc)
    item: dict[str, Any] = {
        "PK": f"JOB#{correlation_id}",
        "SK": "JOB_STATUS",
        "status": "IN_PROGRESS",
        "request_type": request_type,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "ttl": int(now.timestamp()) + JOB_TTL_SECONDS,
    }
    if league_id:
        item["league_id"] = league_id
    if platform:
        item["platform"] = platform
    if canonical_league_id:
        item["canonical_league_id"] = canonical_league_id
    try:
        main.table.put_item(Item=item)
    except botocore.exceptions.ClientError as e:
        logger.error("Failed to create JOB_STATUS for %s: %s", correlation_id, e)


def get_job_status(correlation_id: str) -> dict | None:
    """
    Fetch a job's JOB_STATUS item, or None if it has expired / never existed.

    Args:
        correlation_id: The job's correlation ID.

    Returns:
        The JOB_STATUS item dict, or None.
    """
    try:
        response = main.table.get_item(
            Key={"PK": f"JOB#{correlation_id}", "SK": "JOB_STATUS"}
        )
    except botocore.exceptions.ClientError as e:
        logger.error("Boto error occurred: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve job status",
        )
    return response.get("Item")


def set_active_job(canonical_league_id: str, correlation_id: str) -> None:
    """
    Point a league's METADATA at its in-flight job (concurrency-guard pointer).

    Stores ``active_job_id`` on METADATA so a subsequent request can dereference
    the current job and reject duplicates while it is IN_PROGRESS. Best-effort.

    Args:
        canonical_league_id: The canonical league ID (must already have METADATA).
        correlation_id: The job's correlation ID to record as active.
    """
    try:
        main.table.update_item(
            Key={"PK": f"LEAGUE#{canonical_league_id}", "SK": "METADATA"},
            UpdateExpression="SET active_job_id = :j",
            ExpressionAttributeValues={":j": correlation_id},
        )
    except botocore.exceptions.ClientError as e:
        logger.error("Failed to set active_job_id for %s: %s", canonical_league_id, e)


def is_job_in_progress(metadata: dict) -> bool:
    """
    Whether a league has an in-flight onboard/refresh/migrate job.

    Dereferences the METADATA ``active_job_id`` pointer to the JOB_STATUS item;
    a missing/expired job or a terminal status means no job is in progress (the
    JOB_STATUS TTL also releases stuck jobs after 24h).

    Args:
        metadata: The league's METADATA item.

    Returns:
        True only if the referenced job exists and is IN_PROGRESS.
    """
    active_job_id = metadata.get("active_job_id")
    if not active_job_id:
        return False
    job = get_job_status(active_job_id)
    return bool(job) and job.get("status") == "IN_PROGRESS"


def update_league_count(delta: int) -> None:
    main.table.update_item(
        Key={"PK": "APP#STATS", "SK": "LEAGUE_COUNT"},
        UpdateExpression="ADD league_count :delta",
        ExpressionAttributeValues={":delta": Decimal(str(delta))},
    )


def require_active_subscription(
    canonical_league_id: str, metadata: dict | None = None
) -> None:
    """
    Gate access to a league based on its subscription.

    A league's subscription is active while ``now < subscription_end_time``.
    An absent or past ``subscription_end_time`` is treated as expired and raises
    ``402 Payment Required`` so the caller (frontend) can surface a paywall.

    Args:
        canonical_league_id: The canonical league ID.
        metadata: Optional pre-fetched METADATA item; when omitted it is read
            from DynamoDB. Pass it to avoid a redundant read when the caller has
            already loaded the league's metadata.

    Raises:
        HTTPException: 402 when the subscription is expired or absent.
    """
    if metadata is None:
        metadata = get_league_metadata(canonical_league_id)
    subscription_end_time = metadata.get("subscription_end_time")
    if subscription_end_time:
        try:
            end_dt = datetime.fromisoformat(subscription_end_time)
            if end_dt > datetime.now(timezone.utc):
                return
        except ValueError:
            logger.warning(
                "Unparseable subscription_end_time %r for league %s; treating as expired",
                subscription_end_time,
                canonical_league_id,
            )
    raise HTTPException(
        status_code=status.HTTP_402_PAYMENT_REQUIRED,
        detail="Subscription required",
    )


def _is_conditional_check_failure(exc: botocore.exceptions.ClientError) -> bool:
    """True when a DynamoDB ClientError is a failed ConditionExpression."""
    return (
        exc.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException"
    )


def get_stripe_customer_id(clerk_user_id: str) -> str | None:
    """Return the Stripe customer ID mapped to a Clerk user, or None if unmapped.

    Reads the ``USER#{clerk_user_id}`` item (BE-015).
    """
    try:
        response = main.table.get_item(
            Key={"PK": f"USER#{clerk_user_id}", "SK": "USER"}
        )
    except botocore.exceptions.ClientError as e:
        logger.error("Boto error reading user mapping: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to look up billing account",
        )
    return response.get("Item", {}).get("stripe_customer_id")


def trial_used_for_league(native_league_id: str, platform) -> bool:
    """Return True if this platform league has ever consumed its free trial (BE-015).

    Reads the durable ``TRIAL_USED`` marker keyed by the platform-native identity
    ``(platform, native_league_id)``. Unlike the ``METADATA`` ``trial_used`` flag,
    this marker survives league deletion, so a deleted-then-re-onboarded league is
    not granted a second trial.
    """
    pk = f"LEAGUE#{native_league_id}#PLATFORM#{platform.value}"
    try:
        response = main.table.get_item(Key={"PK": pk, "SK": "TRIAL_USED"})
    except botocore.exceptions.ClientError as e:
        logger.error("Boto error reading trial-used marker: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to look up trial eligibility",
        )
    return "Item" in response


def get_or_create_stripe_customer(clerk_user_id: str) -> str:
    """Resolve (or lazily create) the Stripe customer for a Clerk user.

    Looks up the stored ``USER#{clerk_user_id}`` mapping first; when absent,
    creates a Stripe Customer with an idempotency key derived from the Clerk user
    ID (so concurrent first-checkout requests resolve to the *same* customer) and
    persists the mapping with a conditional write. If a concurrent request wins
    the write, the existing mapping is re-read and returned (BE-015 Idempotency
    Layer 1).

    Args:
        clerk_user_id: The authenticated Clerk user ID (JWT ``sub``).

    Returns:
        The Stripe customer ID.
    """
    existing = get_stripe_customer_id(clerk_user_id)
    if existing:
        return existing

    customer = main.stripe.Customer.create(
        metadata={"clerk_user_id": clerk_user_id},
        idempotency_key=f"customer:{clerk_user_id}",
    )
    customer_id = customer["id"]

    try:
        main.table.put_item(
            Item={
                "PK": f"USER#{clerk_user_id}",
                "SK": "USER",
                "stripe_customer_id": customer_id,
            },
            ConditionExpression="attribute_not_exists(PK)",
        )
        return customer_id
    except botocore.exceptions.ClientError as e:
        if not _is_conditional_check_failure(e):
            logger.error("Boto error writing user mapping: %s", e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to set up billing account",
            )
        # A concurrent request created the mapping first. Because the customer
        # create used a clerk-user-scoped idempotency key, both calls resolved to
        # the same Stripe customer, so the stored value matches ours.
        return get_stripe_customer_id(clerk_user_id) or customer_id


def _is_missing_customer_error(error: stripe.error.InvalidRequestError) -> bool:
    """Return True when a Stripe error reports a missing/deleted customer (BE-015).

    Stripe returns ``param == "customer"`` (with a "No such customer" message) when
    a Checkout Session is opened against a customer that was deleted out-of-band in
    the Stripe dashboard.
    """
    return getattr(error, "param", None) == "customer"


def recreate_stripe_customer(clerk_user_id: str) -> str:
    """Mint a fresh Stripe customer for a user whose stored customer was deleted.

    Checkout recovery (BE-015): when the ``USER#{clerk_user_id}`` mapping points at
    a customer that no longer exists in Stripe, create a new customer and overwrite
    the stored mapping so subsequent billing calls resolve correctly. Unlike
    ``get_or_create_stripe_customer`` (which keys the idempotency key on the user),
    this uses a unique key so the create is **not** deduplicated back to the deleted
    customer, and overwrites the mapping unconditionally (the old value is invalid).

    Args:
        clerk_user_id: The authenticated Clerk user ID (JWT ``sub``).

    Returns:
        The new Stripe customer ID.
    """
    customer = main.stripe.Customer.create(
        metadata={"clerk_user_id": clerk_user_id},
        idempotency_key=f"customer:{clerk_user_id}:{uuid.uuid4().hex}",
    )
    customer_id = customer["id"]
    try:
        main.table.put_item(
            Item={
                "PK": f"USER#{clerk_user_id}",
                "SK": "USER",
                "stripe_customer_id": customer_id,
            }
        )
    except botocore.exceptions.ClientError as e:
        logger.error("Boto error updating user mapping: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set up billing account",
        )
    return customer_id


def create_subscription_checkout_session(
    customer_id: str,
    clerk_user_id: str,
    subscription_data: dict[str, Any],
    token: str,
) -> Any:
    """Open a subscription-mode Checkout Session, recovering from a deleted customer.

    BE-015: the stored Stripe customer can be deleted out-of-band, in which case
    ``checkout.Session.create`` raises a "No such customer" ``InvalidRequestError``.
    When that happens we mint a fresh customer (``recreate_stripe_customer``),
    persist the new mapping, and retry the session **once** with a new idempotency
    key. Any other Stripe error surfaces as a ``502`` (with a JSON ``detail`` and
    CORS headers) so the frontend can show it inline — rather than an uncaught
    ``500`` raised above the CORS middleware, which the browser cannot read.

    Args:
        customer_id: The caller's resolved Stripe customer ID.
        clerk_user_id: The authenticated Clerk user ID, used to recreate a deleted
            customer.
        subscription_data: ``subscription_data`` for the Checkout Session (metadata
            and optional trial).
        token: The per-attempt nonce used as the Stripe idempotency key.

    Returns:
        The created Stripe Checkout Session object.
    """

    def _create(cust_id: str, idempotency_key: str) -> Any:
        return main.stripe.checkout.Session.create(
            mode="subscription",
            customer=cust_id,
            line_items=[{"price": main.STRIPE_PRICE_ID, "quantity": 1}],
            subscription_data=subscription_data,
            allow_promotion_codes=True,
            managed_payments={"enabled": True},
            success_url=main.STRIPE_CHECKOUT_SUCCESS_URL,
            cancel_url=main.STRIPE_CHECKOUT_CANCEL_URL,
            idempotency_key=idempotency_key,
        )

    try:
        return _create(customer_id, token)
    except stripe.error.InvalidRequestError as e:
        if not _is_missing_customer_error(e):
            logger.error("Stripe rejected checkout session create: %s", e)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Couldn't start checkout. Please try again.",
            )
        logger.warning(
            "Stripe customer %s no longer exists; recreating for user %s",
            customer_id,
            clerk_user_id,
        )
        new_customer_id = recreate_stripe_customer(clerk_user_id)
        try:
            return _create(new_customer_id, f"{token}-retry")
        except stripe.error.StripeError as retry_error:
            logger.error(
                "Checkout retry after customer recreation failed: %s", retry_error
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Couldn't start checkout. Please try again.",
            )
    except stripe.error.StripeError as e:
        logger.error("Stripe error creating checkout session: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Couldn't start checkout. Please try again.",
        )


def cancel_league_subscription(stripe_subscription_id: str | None) -> None:
    """Immediately cancel a league's Stripe subscription on delete (BE-007 / BE-015).

    Called by ``delete_league`` **before** any league data is removed, so a failed
    cancellation aborts the delete with the league (and its ``stripe_subscription_id``)
    intact for retry — the data is never destroyed while a live subscription still
    points at it. Cancellation is immediate, consistent with BE-015's policy.

    Idempotent: a missing id (league never subscribed) is a no-op, and an
    already-canceled / no-longer-existent subscription (Stripe ``InvalidRequestError``)
    is treated as success. Any other Stripe error raises ``HTTPException(500)`` so the
    caller leaves the league's data in place.

    Args:
        stripe_subscription_id: The league's recorded subscription, or ``None`` when
            the league has no subscription to cancel.
    """
    if not stripe_subscription_id:
        return
    try:
        main.stripe.Subscription.cancel(
            stripe_subscription_id,
            idempotency_key=f"delete-league-sub:{stripe_subscription_id}",
        )
        logger.info("Canceled subscription %s on league delete", stripe_subscription_id)
    except stripe.error.InvalidRequestError as e:
        # Already canceled or no longer exists in Stripe — nothing to do.
        logger.info(
            "Subscription %s already canceled/absent; treating as success: %s",
            stripe_subscription_id,
            e,
        )
    except stripe.error.StripeError as e:
        logger.error("Failed to cancel subscription %s: %s", stripe_subscription_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel subscription",
        )


def claim_pending_checkout(
    canonical_league_id: str, token: str, clerk_user_id: str
) -> bool:
    """Atomically claim the in-flight checkout slot for a league (BE-015 Layer 1).

    Writes a ``pending_checkout`` marker on the league's METADATA only when the
    league has no recorded subscription and either has no in-flight checkout, the
    existing one has expired, **or** the existing one belongs to the same user
    (so a user who abandoned their own checkout can retry immediately). DynamoDB
    serializes concurrent attempts, so exactly one wins; the marker's
    ``expires_at`` lets an abandoned checkout self-heal for *other* users, and
    reconciliation backstops any true duplicate subscription.

    Args:
        canonical_league_id: The canonical league ID.
        token: A per-attempt nonce (also used as the Stripe idempotency key).
        clerk_user_id: The authenticated user starting the checkout; recorded on
            the marker so the same user can re-claim it.

    Returns:
        ``True`` when the slot was claimed; ``False`` when the league already has
        a subscription or another user holds an unexpired in-flight checkout.
    """
    now = datetime.now(timezone.utc)
    expires_at = (
        now + timedelta(minutes=main.CHECKOUT_PENDING_TTL_MINUTES)
    ).isoformat()
    try:
        main.table.update_item(
            Key={"PK": f"LEAGUE#{canonical_league_id}", "SK": "METADATA"},
            UpdateExpression="SET pending_checkout = :pc",
            ConditionExpression=(
                "attribute_exists(PK) "
                "AND attribute_not_exists(stripe_subscription_id) "
                "AND (attribute_not_exists(pending_checkout) "
                "OR pending_checkout.expires_at < :now "
                "OR pending_checkout.user_id = :uid)"
            ),
            ExpressionAttributeValues={
                ":pc": {
                    "token": token,
                    "expires_at": expires_at,
                    "user_id": clerk_user_id,
                },
                ":now": now.isoformat(),
                ":uid": clerk_user_id,
            },
        )
        return True
    except botocore.exceptions.ClientError as e:
        if _is_conditional_check_failure(e):
            return False
        logger.error("Boto error claiming pending checkout: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start checkout",
        )
