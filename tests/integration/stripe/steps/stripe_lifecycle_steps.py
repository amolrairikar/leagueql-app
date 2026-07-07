import time
from datetime import datetime, timedelta, timezone

import stripe
from behave import given, then, when

# How long to wait for Stripe to deliver the webhook and the deployed handler to
# converge subscription_end_time onto the league METADATA (delivery is async).
_POLL_TIMEOUT = timedelta(minutes=4)
_POLL_INTERVAL_SECONDS = 5

# A declined card grants no access, so there is no positive write to wait for.
# Instead hold for a settle window — long enough for the (created) webhook to be
# delivered and processed — while continuously asserting access is never granted.
_NO_ACCESS_SETTLE = timedelta(seconds=45)


def _stripe(context):
    stripe.api_key = context.stripe_secret_key
    return stripe


def _metadata_item(context):
    resp = context.dynamodb_client.get_item(
        TableName=context.table_name,
        Key={
            "PK": {"S": f"LEAGUE#{context.test_canonical_id}"},
            "SK": {"S": "METADATA"},
        },
    )
    return resp.get("Item", {})


def _create_subscription(context, *, payment_method, trial_period_days=None):
    """Create a test-mode subscription for the league via the Stripe API.

    Attaches the given test payment method — the API equivalent of the
    docs/testing/stripe-test-payments.md cards (``pm_card_visa`` for the
    ``4242 4242 4242 4242`` success card; ``pm_card_chargeCustomerFail`` for the
    ``4000 0000 0000 0341`` card, which *attaches* fine but fails when charged —
    the decline must surface at charge time, not attach time, since the bare
    decline card ``pm_card_chargeDeclined`` is rejected on attach) — and carries
    the league's native identity in the subscription metadata, exactly as the
    checkout endpoint does, so the deployed webhook routes the event back to the
    league. With no trial the first charge is attempted immediately
    (``allow_incomplete``), so a charge-failing card lands the subscription in
    ``incomplete`` rather than silently trialing.
    """
    s = _stripe(context)
    customer = s.Customer.create(
        metadata={"integration_test": "leagueql-stripe-lifecycle"},
    )
    context.cleanup_customer_ids.append(customer["id"])

    attached = s.PaymentMethod.attach(payment_method, customer=customer["id"])
    s.Customer.modify(
        customer["id"],
        invoice_settings={"default_payment_method": attached["id"]},
    )

    params = {
        "customer": customer["id"],
        "items": [{"price": context.stripe_price_id}],
        "metadata": {
            "canonical_league_id": context.test_canonical_id,
            "platform": context.platform,
            "native_league_id": context.test_league_id,
            # Marks this as a CI subscription so the deployed webhook converges
            # subscription state (what these scenarios assert) but skips the
            # recap enqueue — no Bedrock spend / recap writes on the shared dev
            # league (BE-021).
            "integration_test": "leagueql-stripe-lifecycle",
        },
    }
    if trial_period_days is not None:
        params["trial_period_days"] = trial_period_days
    else:
        params["payment_behavior"] = "allow_incomplete"

    subscription = s.Subscription.create(**params)
    context.cleanup_subscription_ids.append(subscription["id"])
    context.subscription_id = subscription["id"]
    return subscription


def _create_trialing_subscription(context):
    subscription = _create_subscription(
        context, payment_method="pm_card_visa", trial_period_days=14
    )
    context.expected_trial_end = int(subscription["trial_end"])


def _poll_until(context, predicate, failure_message):
    deadline = datetime.now(timezone.utc) + _POLL_TIMEOUT
    while datetime.now(timezone.utc) < deadline:
        if predicate(_metadata_item(context)):
            return
        time.sleep(_POLL_INTERVAL_SECONDS)
    raise AssertionError(failure_message)


@given("the league has no recorded subscription")
def step_clear_subscription_state(context):
    # Start from a clean slate regardless of leftover state from a prior run, so
    # the monotonic / duplicate guards in common.subscription don't reject the
    # new test subscription.
    context.dynamodb_client.update_item(
        TableName=context.table_name,
        Key={
            "PK": {"S": f"LEAGUE#{context.test_canonical_id}"},
            "SK": {"S": "METADATA"},
        },
        UpdateExpression=(
            "REMOVE stripe_subscription_id, subscription_end_time, pending_checkout"
        ),
    )


@given("a trialing subscription has been recorded for the league")
def step_subscription_recorded(context):
    _create_trialing_subscription(context)
    # The cancel path's expire write is scoped to the recorded subscription, so
    # wait until the created webhook has claimed stripe_subscription_id first.
    _poll_until(
        context,
        lambda item: (
            item.get("stripe_subscription_id", {}).get("S") == context.subscription_id
        ),
        "webhook did not record stripe_subscription_id on the league within the timeout",
    )


@when("a trialing subscription is created for the league with the test card")
def step_create_subscription(context):
    _create_trialing_subscription(context)


@when("the subscription is canceled")
def step_cancel_subscription(context):
    _stripe(context).Subscription.cancel(context.subscription_id)


@when("a no-trial subscription is created for the league with a declined card")
def step_create_declined_subscription(context):
    # pm_card_chargeCustomerFail attaches successfully but fails when charged, so
    # the decline surfaces on the subscription's first invoice (status incomplete)
    # rather than at attach time.
    _create_subscription(context, payment_method="pm_card_chargeCustomerFail")


@then("subscription_end_time on the league converges to the subscription trial_end")
def step_assert_trial_end_recorded(context):
    def _recorded(item):
        end = item.get("subscription_end_time", {}).get("S")
        if not end:
            return False
        # The webhook writes iso(trial_end); accept only this subscription's value.
        return (
            int(datetime.fromisoformat(end).timestamp()) == context.expected_trial_end
        )

    _poll_until(
        context,
        _recorded,
        "subscription_end_time did not converge to the subscription trial_end "
        "within the timeout",
    )
    item = _metadata_item(context)
    assert item.get("stripe_subscription_id", {}).get("S") == context.subscription_id, (
        "stripe_subscription_id was not claimed for the recorded subscription"
    )


@then("subscription_end_time on the league is set to the past")
def step_assert_expired(context):
    now = datetime.now(timezone.utc)

    def _expired(item):
        end = item.get("subscription_end_time", {}).get("S")
        return bool(end) and datetime.fromisoformat(end) < now

    _poll_until(
        context,
        _expired,
        "subscription_end_time was not expired (set to the past) within the timeout",
    )


@then("the league is not granted access")
def step_assert_no_access(context):
    # The declined immediate charge lands the subscription in `incomplete`, which
    # the webhook treats as "no state change" — so subscription_end_time is never
    # written and stripe_subscription_id is never claimed. Hold for a settle window
    # (giving the created webhook time to be delivered and processed) and assert no
    # access is granted at any point.
    deadline = datetime.now(timezone.utc) + _NO_ACCESS_SETTLE
    while datetime.now(timezone.utc) < deadline:
        item = _metadata_item(context)
        end = item.get("subscription_end_time", {}).get("S")
        assert not end or datetime.fromisoformat(end) < datetime.now(timezone.utc), (
            f"declined card unexpectedly granted access: subscription_end_time={end}"
        )
        assert (
            item.get("stripe_subscription_id", {}).get("S") != context.subscription_id
        ), "declined subscription was unexpectedly recorded on the league"
        time.sleep(_POLL_INTERVAL_SECONDS)
