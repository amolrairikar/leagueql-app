"""Steps for the per-user league membership index + GET /me/leagues (backend/user-leagues).

Index assertions query the real (moto) GSI4, so they prove the item carries the right
index keys rather than just existing under the league partition.
"""

from behave import given, then, when
from boto3.dynamodb.conditions import Key
from common_steps import load_fixture, put_item
from onboarding_steps import _patch_build_client, _run_onboarder


def _indexed_canonicals(context, user_id) -> list[str]:
    table = context.ddb_resource.Table(context.table_name)
    resp = table.query(
        IndexName="GSI4", KeyConditionExpression=Key("member_user_id").eq(user_id)
    )
    return [item["PK"].removeprefix("LEAGUE#") for item in resp["Items"]]


@given('user "{user_id}" is indexed for league "{canonical}"')
def step_seed_member(context, user_id, canonical):
    put_item(
        context,
        {
            "PK": f"LEAGUE#{canonical}",
            "SK": f"MEMBER#{user_id}",
            "member_user_id": user_id,
            "joined_at": "2026-01-01T00:00:00+00:00",
        },
    )


@when(
    'user "{user_id}" onboards "{platform}" league "{league_id}" '
    'with fixture "{fixture}"'
)
def step_onboard_owned(context, platform, league_id, user_id, fixture):
    _patch_build_client(context, load_fixture(*fixture.split("/")))
    _run_onboarder(
        context, platform, league_id, "ONBOARD", event_extra={"ownerUserId": user_id}
    )


@then('user "{user_id}" is indexed for league "{canonical}"')
def step_is_indexed(context, user_id, canonical):
    found = _indexed_canonicals(context, user_id)
    assert found.count(canonical) == 1, found


@then('user "{user_id}" is indexed for the onboarded league')
def step_is_indexed_onboarded(context, user_id):
    step_is_indexed(context, user_id, context.canonical)


@then('user "{user_id}" is not indexed for league "{canonical}"')
def step_is_not_indexed(context, user_id, canonical):
    found = _indexed_canonicals(context, user_id)
    assert canonical not in found, found


@then("the onboarded league indexes no one")
def step_onboarded_indexes_no_one(context):
    table = context.ddb_resource.Table(context.table_name)
    resp = table.query(
        KeyConditionExpression=Key("PK").eq(f"LEAGUE#{context.canonical}")
        & Key("SK").begins_with("MEMBER#")
    )
    assert resp["Items"] == [], resp["Items"]


@given("the request is unauthenticated")
def step_unauthenticated(context):
    import routes

    context.main.app.dependency_overrides.pop(routes.get_authenticated_user, None)


@then('my leagues list league "{league_id}" on "{platform}"')
def step_my_leagues_include(context, league_id, platform):
    leagues = context.response.json()["data"]
    assert any(
        lg["league_id"] == league_id and lg["platform"] == platform for lg in leagues
    ), leagues


@then("my leagues list is empty")
def step_my_leagues_empty(context):
    assert context.response.json()["data"] == [], context.response.json()
