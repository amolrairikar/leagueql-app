"""Steps for the Stripe billing webhook component (BE-015).

``stripe.Webhook.construct_event`` and ``stripe.Subscription.retrieve/.cancel`` are
patched so no real Stripe call is made; everything else (the dedup ``WEBHOOK_EVENT``
item, the conditional ``common.subscription`` writes, the durable trial marker) runs
against moto.
"""

import json
import time
from unittest.mock import MagicMock, patch

import stripe
from behave import given, then, when
from common_steps import get_item, put_item

FUTURE_TS = int(time.time()) + 30 * 24 * 60 * 60


@given('a subscribable league "{canonical}" native "{league_id}" on "{platform}"')
def step_subscribable_league(context, canonical, league_id, platform):
    # METADATA with no subscription_end_time yet (the webhook is its sole writer).
    put_item(
        context,
        {
            "PK": f"LEAGUE#{canonical}",
            "SK": "METADATA",
            "platform": platform,
            "native_league_id": league_id,
        },
    )
    context.stripe_canonical = canonical
    context.stripe_native = league_id
    context.stripe_platform = platform


@given(
    'a checkout-ready league "{canonical}" native "{league_id}" on "{platform}" '
    'for user "{user_id}"'
)
def step_checkout_ready_league(context, canonical, league_id, platform, user_id):
    # LEAGUE_LOOKUP (resolved by lookup_league) + METADATA with trial_used already
    # set, so the endpoint reaches Session.create without the trial-eligibility read.
    put_item(
        context,
        {
            "PK": f"LEAGUE#{league_id}#PLATFORM#{platform}",
            "SK": "LEAGUE_LOOKUP",
            "canonical_league_id": canonical,
        },
    )
    put_item(
        context,
        {
            "PK": f"LEAGUE#{canonical}",
            "SK": "METADATA",
            "platform": platform,
            "native_league_id": league_id,
            "trial_used": True,
            # The checkout caller must be the league owner (LQL-01 / BE-016).
            "owner_user_id": user_id,
        },
    )


@given(
    'user "{user_id}" has a stored Stripe customer "{customer_id}" that was '
    "deleted in Stripe"
)
def step_stored_deleted_customer(context, user_id, customer_id):
    put_item(
        context,
        {"PK": f"USER#{user_id}", "SK": "USER", "stripe_customer_id": customer_id},
    )


@when('user "{user_id}" starts checkout for league "{league_id}" on "{platform}"')
def step_start_checkout(context, user_id, league_id, platform):
    import routes

    # Authenticate as the given user for the duration of the request.
    override = patch.dict(
        context.main.app.dependency_overrides,
        {routes.get_authenticated_user: lambda: user_id},
    )
    override.start()
    context._patches.append(override)

    # The stored customer no longer exists in Stripe: the first session create
    # raises "No such customer"; after the customer is recreated, the retry wins.
    create = patch.object(
        context.main.stripe.checkout.Session,
        "create",
        MagicMock(
            side_effect=[
                stripe.error.InvalidRequestError("No such customer", "customer"),
                {"url": "https://stripe.test/checkout/new"},
            ]
        ),
    )
    create.start()
    context._patches.append(create)

    recreate = patch.object(
        context.main.stripe.Customer,
        "create",
        MagicMock(return_value={"id": "cus_new"}),
    )
    recreate.start()
    context._patches.append(recreate)

    context.response = context.api.post(
        f"/leagues/{league_id}/checkout-session?platform={platform}&plan=MONTHLY"
    )


@then("the checkout endpoint responds 200 with a session URL")
def step_checkout_ok(context):
    assert context.response.status_code == 200, context.response.text
    assert context.response.json()["data"]["url"], context.response.text


@then('user "{user_id}" now maps to a freshly created Stripe customer')
def step_new_customer_mapping(context, user_id):
    item = get_item(context, f"USER#{user_id}", "USER")
    assert item.get("stripe_customer_id") == "cus_new", item


@given('league "{canonical}" already records subscription "{sub_id}"')
def step_existing_subscription(context, canonical, sub_id):
    table = context.ddb_resource.Table(context.table_name)
    table.update_item(
        Key={"PK": f"LEAGUE#{canonical}", "SK": "METADATA"},
        UpdateExpression="SET stripe_subscription_id = :s, subscription_end_time = :t",
        ExpressionAttributeValues={
            ":s": sub_id,
            ":t": "2999-01-01T00:00:00+00:00",
        },
    )


@given('league "{canonical}" has subscription "{sub_id}" with end time "{end_time}"')
def step_existing_subscription_ending(context, canonical, sub_id, end_time):
    # Like the prior step, but with a caller-chosen (earlier) end time so a renewal
    # write is observably an *advance* rather than a no-op.
    table = context.ddb_resource.Table(context.table_name)
    table.update_item(
        Key={"PK": f"LEAGUE#{canonical}", "SK": "METADATA"},
        UpdateExpression="SET stripe_subscription_id = :s, subscription_end_time = :t",
        ExpressionAttributeValues={":s": sub_id, ":t": end_time},
    )


def _build_subscription(sub_id, status, canonical, platform, native):
    sub = {
        "id": sub_id,
        "status": status,
        "metadata": {
            "canonical_league_id": canonical,
            "platform": platform,
            "native_league_id": native,
        },
    }
    if status == "trialing":
        sub["trial_end"] = FUTURE_TS
    else:
        sub["current_period_end"] = FUTURE_TS
    return sub


def _send_event(context, event):
    context._patches.append(
        patch.object(stripe.Webhook, "construct_event", MagicMock(return_value=event))
    )
    context._patches[-1].start()
    api_event = {
        "body": json.dumps(event),
        "headers": {"Stripe-Signature": "sig"},
        "isBase64Encoded": False,
    }
    context.stripe_response = context.stripe_handler.lambda_handler(api_event, None)


@when(
    'Stripe sends a "{event_type}" webhook (event "{event_id}") for subscription '
    '"{sub_id}" with status "{status}"'
)
def step_send_webhook(context, event_type, event_id, sub_id, status):
    canonical = context.stripe_canonical
    platform = context.stripe_platform
    native = context.stripe_native
    subscription = _build_subscription(sub_id, status, canonical, platform, native)

    retrieve = patch.object(
        stripe.Subscription, "retrieve", MagicMock(return_value=subscription)
    )
    retrieve.start()
    context._patches.append(retrieve)
    cancel_patch = patch.object(stripe.Subscription, "cancel", MagicMock())
    context.cancel_mock = cancel_patch.start()
    context._patches.append(cancel_patch)

    if event_type in (
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
    ):
        # The event's data object IS the subscription (carries id + metadata).
        obj = subscription
    else:
        # checkout.session.completed / invoice.paid reference the subscription.
        obj = {"subscription": sub_id}
    event = {"id": event_id, "type": event_type, "data": {"object": obj}}
    _send_event(context, event)


@when("Stripe sends a webhook with an invalid signature")
def step_bad_signature(context):
    def _raise(*args, **kwargs):
        raise stripe.error.SignatureVerificationError("bad", "sig")

    context._patches.append(
        patch.object(stripe.Webhook, "construct_event", MagicMock(side_effect=_raise))
    )
    context._patches[-1].start()
    api_event = {
        "body": "{}",
        "headers": {"Stripe-Signature": "bad"},
        "isBase64Encoded": False,
    }
    context.stripe_response = context.stripe_handler.lambda_handler(api_event, None)


@then("the webhook responds with status {code:d}")
def step_webhook_status(context, code):
    assert context.stripe_response["statusCode"] == code, context.stripe_response


@then('league "{canonical}" has a subscription_end_time')
def step_has_sub_end(context, canonical):
    item = get_item(context, f"LEAGUE#{canonical}", "METADATA")
    assert item.get("subscription_end_time"), item


@then('league "{canonical}" subscription_end_time is later than "{end_time}"')
def step_sub_end_advanced(context, canonical, end_time):
    item = get_item(context, f"LEAGUE#{canonical}", "METADATA")
    stored = item.get("subscription_end_time")
    # Both values are ISO 8601 UTC (same format + offset), so lexical order == time order.
    assert stored and stored > end_time, (stored, end_time)


@then('league "{canonical}" still records subscription "{sub_id}"')
def step_still_records_subscription(context, canonical, sub_id):
    item = get_item(context, f"LEAGUE#{canonical}", "METADATA")
    assert item.get("stripe_subscription_id") == sub_id, item


@then("the subscription was not canceled")
def step_sub_not_canceled(context):
    assert not context.cancel_mock.called, "cancel unexpectedly called"


@then('league "{canonical}" subscription is expired')
def step_sub_expired(context, canonical):
    item = get_item(context, f"LEAGUE#{canonical}", "METADATA")
    assert item.get("subscription_end_time") == "1970-01-01T00:00:00+00:00", item


@then(
    'a durable TRIAL_USED marker exists for native league "{league_id}" on "{platform}"'
)
def step_trial_marker(context, league_id, platform):
    item = get_item(context, f"LEAGUE#{league_id}#PLATFORM#{platform}", "TRIAL_USED")
    assert item, "durable TRIAL_USED marker missing"
    assert "canonical_league_id" not in item, "marker must not carry canonical id"


@then('a WEBHOOK_EVENT dedup marker exists for event "{event_id}"')
def step_webhook_marker(context, event_id):
    assert get_item(context, f"WEBHOOK_EVENT#{event_id}", "WEBHOOK_EVENT"), "no dedup"


@then('no WEBHOOK_EVENT dedup marker exists for event "{event_id}"')
def step_no_webhook_marker(context, event_id):
    assert not get_item(context, f"WEBHOOK_EVENT#{event_id}", "WEBHOOK_EVENT")


@then("the duplicate subscription was canceled")
def step_dup_canceled(context):
    assert context.cancel_mock.called, "cancel not called"


@then('the recap generator was invoked for league "{canonical}"')
def step_recap_invoked_for_league(context, canonical):
    # BE-022: a real activation launches the recap-generator Fargate task (mocked spy).
    spy = context.recap_ecs_client
    assert spy.run_task.called, "recap generator task was not launched"
    overrides = spy.run_task.call_args.kwargs["overrides"]["containerOverrides"][0]
    env = {e["name"]: e["value"] for e in overrides["environment"]}
    assert env["CANONICAL_LEAGUE_ID"] == canonical


@then("the recap generator was invoked {count:d} time")
def step_recap_invoked_n_times(context, count):
    assert context.recap_ecs_client.run_task.call_count == count, (
        f"expected {count} recap task launch(es), got "
        f"{context.recap_ecs_client.run_task.call_count}"
    )
