"""Steps for league ownership + ESPN read authorization (backend/league-authorization).

Requests go through the real ``TestClient`` (``context.api``); the Clerk auth
dependency is overridden per step, and METADATA is read back from moto-backed
DynamoDB for assertions.
"""

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


@when('I POST an invite token for league "{league_id}" on "{platform}"')
def step_mint_invite_token(context, league_id, platform):
    context.response = context.api.post(
        f"/leagues/{league_id}/invite-token?platform={platform}"
    )
    if context.response.status_code == 200:
        context.invite_token = context.response.json()["data"]["token"]


@when(
    'I accept the invite for league "{league_id}" on "{platform}" with the minted token'
)
def step_accept_invite_minted(context, league_id, platform):
    context.response = context.api.post(
        f"/leagues/{league_id}/accept-invite?platform={platform}",
        json={"token": context.invite_token},
    )


@when(
    'I accept the invite for league "{league_id}" on "{platform}" with token "{token}"'
)
def step_accept_invite_token(context, league_id, platform, token):
    context.response = context.api.post(
        f"/leagues/{league_id}/accept-invite?platform={platform}",
        json={"token": token},
    )


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
