"""Behave steps for the Yahoo OAuth linking flow (backend/yahoo-oauth)."""

from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlparse

from behave import then, when
from common_steps import get_item


@when('I start the Yahoo authorization for league "{league_id}"')
def step_start_authorize(context, league_id):
    context.response = context.api.get(f"/auth/yahoo/authorize?leagueId={league_id}")
    # Stash the minted state so the callback step can echo it back like Yahoo would.
    authorize_url = context.response.json()["data"]["authorize_url"]
    context.yahoo_state = parse_qs(urlparse(authorize_url).query)["state"][0]


@when("Yahoo redirects back to the callback with a valid code")
def step_callback_valid(context):
    import main

    token_response = MagicMock()
    token_response.json.return_value = {
        "access_token": "yahoo-access-token",
        "refresh_token": "yahoo-refresh-token",
        "token_type": "bearer",
        "expires_in": 3600,
    }
    token_response.raise_for_status.return_value = None
    patcher = patch.object(
        main.http_requests, "post", MagicMock(return_value=token_response)
    )
    patcher.start()
    context._patches.append(patcher)
    context.response = context.api.get(
        f"/auth/yahoo/callback?code=the-code&state={context.yahoo_state}",
        follow_redirects=False,
    )


@when('Yahoo redirects back to the callback with code "{code}" and state "{state}"')
def step_callback_with_state(context, code, state):
    context.response = context.api.get(
        f"/auth/yahoo/callback?code={code}&state={state}", follow_redirects=False
    )


@when('I POST an ONBOARD of league "{league_id}" on "{platform}"')
def step_post_onboard(context, league_id, platform):
    context.response = context.api.post(
        "/leagues", json={"leagueId": league_id, "platform": platform}
    )


@then("the callback redirects with the linked marker")
def step_assert_linked(context):
    assert context.response.status_code == 302, context.response.status_code
    location = context.response.headers["location"]
    assert "platform=YAHOO" in location
    assert "yahooLinked=1" in location


@then("the callback redirects with the not-linked marker")
def step_assert_not_linked(context):
    assert context.response.status_code == 302, context.response.status_code
    assert "yahooLinked=0" in context.response.headers["location"]


@then("a YAHOO_OAUTH token item exists for the default user with encrypted tokens")
def step_assert_token_item(context):
    item = get_item(context, f"USER#{context.default_user}", "YAHOO_OAUTH")
    assert item is not None, "expected a YAHOO_OAUTH item"
    # Tokens are stored as KMS ciphertext, never the plaintext values.
    plaintext_access = "yahoo-access-token"  # matches the mocked token exchange
    plaintext_refresh = "yahoo-refresh-token"
    assert item["access_token"] != plaintext_access
    assert item["refresh_token"] != plaintext_refresh
    assert int(item["expires_at"]) > 0
