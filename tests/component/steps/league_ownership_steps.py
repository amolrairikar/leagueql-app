"""Steps for league ownership + ESPN read authorization (backend/league-authorization).

Requests go through the real ``TestClient`` (``context.api``); the Clerk auth
dependency is overridden per step, ESPN HTTP is patched where verify-membership
reaches out, and METADATA is read back from moto-backed DynamoDB for assertions.
"""

from unittest.mock import MagicMock, patch

from behave import given, then, when
from common_steps import get_item


def _authenticate(context, user_id):
    import routes

    context.main.app.dependency_overrides[routes.get_authenticated_user] = lambda: (
        user_id
    )


@given('the request is authenticated as "{user_id}"')
def step_authenticate(context, user_id):
    _authenticate(context, user_id)


def _post_verify(context, league_id, platform, code):
    import routes

    resp = MagicMock(status_code=code)
    if code == 200:
        resp.raise_for_status.return_value = None
    else:
        import requests

        err = requests.exceptions.HTTPError("boom")
        err.response = MagicMock(status_code=code)
        resp.raise_for_status.side_effect = err
    patcher = patch.object(routes.http_requests, "get", MagicMock(return_value=resp))
    patcher.start()
    context._patches.append(patcher)
    context.response = context.api.post(
        f"/leagues/{league_id}/verify-membership?platform={platform}",
        json={"swid": "{SWID}", "s2": "s2cookie"},
    )


@when(
    'I POST to verify-membership for league "{league_id}" with ESPN returning {code:d}'
)
def step_verify_membership(context, league_id, code):
    _post_verify(context, league_id, "ESPN", code)


@when(
    'I POST to verify-membership for "{platform}" league "{league_id}" '
    "with ESPN returning {code:d}"
)
def step_verify_membership_platform(context, platform, league_id, code):
    _post_verify(context, league_id, platform, code)


@when('I POST a transfer token for league "{league_id}" on "{platform}"')
def step_mint_transfer_token(context, league_id, platform):
    context.response = context.api.post(
        f"/leagues/{league_id}/transfer-token?platform={platform}"
    )
    if context.response.status_code == 200:
        context.transfer_token = context.response.json()["data"]["token"]


@when('I claim ownership of league "{league_id}" on "{platform}" with the minted token')
def step_claim_with_minted(context, league_id, platform):
    context.response = context.api.post(
        f"/leagues/{league_id}/claim-ownership?platform={platform}",
        json={"token": context.transfer_token},
    )


@when('I claim ownership of league "{league_id}" on "{platform}" with token "{token}"')
def step_claim_with_token(context, league_id, platform, token):
    context.response = context.api.post(
        f"/leagues/{league_id}/claim-ownership?platform={platform}",
        json={"token": token},
    )


@then('user "{user_id}" is a member of league "{canonical}"')
def step_is_member(context, user_id, canonical):
    item = get_item(context, f"LEAGUE#{canonical}", "METADATA")
    assert user_id in (item.get("members") or set()), item


@then('user "{user_id}" is not a member of league "{canonical}"')
def step_is_not_member(context, user_id, canonical):
    item = get_item(context, f"LEAGUE#{canonical}", "METADATA")
    assert user_id not in (item.get("members") or set()), item


@then('user "{user_id}" is the owner of league "{canonical}"')
def step_is_owner(context, user_id, canonical):
    item = get_item(context, f"LEAGUE#{canonical}", "METADATA")
    assert item.get("owner_user_id") == user_id, item
