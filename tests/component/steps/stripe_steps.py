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
