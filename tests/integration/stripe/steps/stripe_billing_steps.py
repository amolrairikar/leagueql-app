from urllib.parse import urlparse

import requests
from behave import given, then, when

REQUEST_TIMEOUT = 30


def _authed_headers(context):
    """Mint a fresh Clerk bearer token for the configured test user."""
    jwt = context.mint_jwt(
        secret_key=context.clerk_secret_key,
        user_id=context.clerk_user_id,
        template=context.clerk_template,
    )
    return {"Authorization": f"Bearer {jwt}"}


def _post_checkout(context, headers):
    return requests.post(
        f"{context.api_base_url}/leagues/{context.test_league_id}/checkout-session",
        params={"platform": context.platform, "plan": "MONTHLY"},
        headers=headers,
        timeout=REQUEST_TIMEOUT,
    )


def _post_billing_portal(context, headers):
    return requests.post(
        f"{context.api_base_url}/billing-portal-session",
        headers=headers,
        timeout=REQUEST_TIMEOUT,
    )


def _assert_stripe_url(context):
    resp = context.response
    assert resp.status_code == 200, f"expected 200, got {resp.status_code}: {resp.text}"
    url = resp.json()["data"]["url"]
    parsed = urlparse(url)
    assert parsed.scheme == "https", f"unexpected URL scheme: {url}"
    # Check the parsed host (not a substring of the whole URL) so a hostile host
    # like ``stripe.com.evil.com`` or ``evil.com/stripe.com`` cannot pass — the
    # Stripe-hosted pages live on stripe.com subdomains (checkout./billing.).
    host = parsed.hostname or ""
    assert host == "stripe.com" or host.endswith(".stripe.com"), (
        f"not a Stripe-hosted URL: {url}"
    )


@given("a Sleeper league exists in DynamoDB")
def step_league_exists(context):
    resp = context.dynamodb_client.get_item(
        TableName=context.table_name,
        Key={
            "PK": {"S": f"LEAGUE#{context.test_league_id}#PLATFORM#{context.platform}"},
            "SK": {"S": "LEAGUE_LOOKUP"},
        },
    )
    item = resp.get("Item")
    assert item, (
        f"Precondition failed: LEAGUE_LOOKUP for {context.test_league_id} not found in "
        "DynamoDB. The Stripe suite must run after the Sleeper onboarding integration tests."
    )
    context.test_canonical_id = item["canonical_league_id"]["S"]


@given("the test league has no in-flight checkout")
def step_clear_pending_checkout(context):
    # Remove any pending_checkout marker left by a prior run so the checkout
    # assertions start from a known-clean state (the marker also self-heals via
    # its TTL, but clearing it makes the test deterministic).
    context.dynamodb_client.update_item(
        TableName=context.table_name,
        Key={
            "PK": {"S": f"LEAGUE#{context.test_canonical_id}"},
            "SK": {"S": "METADATA"},
        },
        UpdateExpression="REMOVE pending_checkout",
    )


@given("the user has an in-flight checkout for the test league")
def step_existing_checkout(context):
    resp = _post_checkout(context, _authed_headers(context))
    assert resp.status_code == 200, (
        f"setup checkout failed: {resp.status_code} {resp.text}"
    )


@given("the user has a Stripe customer")
def step_ensure_customer(context):
    # Opening a checkout session get-or-creates the user's Stripe customer
    # (and persists the USER#{clerk_user_id} mapping), which the billing portal
    # then resolves. Idempotent, so it is safe regardless of prior runs.
    resp = _post_checkout(context, _authed_headers(context))
    assert resp.status_code == 200, (
        f"could not ensure Stripe customer: {resp.status_code} {resp.text}"
    )


@when("the user requests a checkout session for the test league")
def step_request_checkout(context):
    context.response = _post_checkout(context, _authed_headers(context))


@when("an unauthenticated checkout request is made for the test league")
def step_request_checkout_unauth(context):
    context.response = _post_checkout(context, {})


@when("the user requests a billing portal session")
def step_request_portal(context):
    context.response = _post_billing_portal(context, _authed_headers(context))


@when("an unauthenticated billing portal request is made")
def step_request_portal_unauth(context):
    context.response = _post_billing_portal(context, {})


@then("the API responds 200 with a Stripe checkout URL")
def step_assert_checkout_url(context):
    _assert_stripe_url(context)


@then("the API responds 200 with a Stripe billing portal URL")
def step_assert_portal_url(context):
    _assert_stripe_url(context)


@then("a pending_checkout marker is recorded on the league for the user")
def step_assert_marker(context):
    resp = context.dynamodb_client.get_item(
        TableName=context.table_name,
        Key={
            "PK": {"S": f"LEAGUE#{context.test_canonical_id}"},
            "SK": {"S": "METADATA"},
        },
    )
    marker = resp.get("Item", {}).get("pending_checkout", {}).get("M")
    assert marker, "pending_checkout marker not written to METADATA"
    assert marker.get("user_id", {}).get("S") == context.clerk_user_id, (
        "pending_checkout marker does not belong to the checkout initiator"
    )
    assert marker.get("token", {}).get("S"), "pending_checkout marker missing token"


@then("the API rejects the request as unauthorized")
def step_assert_unauthorized(context):
    # API Gateway's JWT authorizer rejects a missing/invalid token with 401
    # before the request reaches the Lambda; accept 403 too for robustness.
    assert context.response.status_code in (401, 403), (
        f"expected 401/403, got {context.response.status_code}: {context.response.text}"
    )
