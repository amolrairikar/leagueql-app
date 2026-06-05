import json

import requests
from behave import then, when

REQUEST_TIMEOUT = 30

# A well-formed event body that can never carry a valid signature for our
# signing secret, so the webhook must reject it at verification.
_EVENT_PAYLOAD = json.dumps(
    {
        "id": "evt_integration_test_invalid_signature",
        "object": "event",
        "type": "checkout.session.completed",
        "data": {"object": {}},
    }
)


def _post_webhook(context, extra_headers):
    return requests.post(
        f"{context.api_base_url}/stripe/webhook",
        data=_EVENT_PAYLOAD,
        headers={"Content-Type": "application/json", **extra_headers},
        timeout=REQUEST_TIMEOUT,
    )


@when("a webhook event is posted with an invalid Stripe-Signature")
def step_post_invalid_signature(context):
    # A syntactically plausible but unverifiable signature header.
    context.response = _post_webhook(
        context, {"Stripe-Signature": "t=1700000000,v1=deadbeefdeadbeefdeadbeef"}
    )


@when("a webhook event is posted with no Stripe-Signature")
def step_post_no_signature(context):
    context.response = _post_webhook(context, {})


@then("the webhook is rejected with 400")
def step_assert_rejected(context):
    assert context.response.status_code == 400, (
        f"expected 400, got {context.response.status_code}: {context.response.text}"
    )
