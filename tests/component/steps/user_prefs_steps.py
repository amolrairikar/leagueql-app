"""Steps for the user league preferences endpoints (backend/user-league-preferences)."""

from behave import given, then, when
from common_steps import get_item, put_item


@given('league "{canonical}" has teams owned by "{owners}"')
def step_seed_team_owners(context, canonical, owners):
    rows = [
        {"team_id": str(i + 1), "season": "2024", "primary_owner_id": owner.strip()}
        for i, owner in enumerate(owners.split(","))
    ]
    put_item(context, {"PK": f"LEAGUE#{canonical}", "SK": "TEAMS#2024", "data": rows})


@given('I PUT my claimed owner "{owner_id}" for "{path}"')
@when('I PUT my claimed owner "{owner_id}" for "{path}"')
def step_put_claim(context, owner_id, path):
    context.response = context.api.put(path, json={"owner_id": owner_id})


@then('no preferences exist for user "{user_id}" in league "{canonical}"')
def step_assert_no_prefs(context, user_id, canonical):
    item = get_item(context, f"LEAGUE#{canonical}", f"USER#{user_id}")
    assert item is None, item
