"""Shared Given/When/Then steps: DynamoDB seeding and generic assertions."""

import json
from pathlib import Path

from behave import given, then, when

_FIXTURES = Path(__file__).parents[1] / "fixtures"


def load_fixture(*parts: str):
    """Load a JSON fixture relative to ``tests/component/fixtures``."""
    with open(_FIXTURES.joinpath(*parts)) as fh:
        return json.load(fh)


def put_item(context, item: dict) -> None:
    """Put a plain-Python item (numbers as needed) via the resource Table."""
    context.ddb_resource.Table(context.table_name).put_item(Item=item)


def get_item(context, pk: str, sk: str) -> dict | None:
    resp = context.ddb_resource.Table(context.table_name).get_item(
        Key={"PK": pk, "SK": sk}
    )
    return resp.get("Item")


@given(
    'a LEAGUE_LOOKUP exists for league "{league_id}" platform "{platform}" '
    'canonical "{canonical}"'
)
def step_seed_lookup(context, league_id, platform, canonical):
    put_item(
        context,
        {
            "PK": f"LEAGUE#{league_id}#PLATFORM#{platform}",
            "SK": "LEAGUE_LOOKUP",
            "canonical_league_id": canonical,
            "seasons": {"2023", "2024"},
            "platform": platform,
            "league_id": league_id,
        },
    )
    # METADATA is read by most league endpoints; seed a permissive one. The default
    # authenticated caller is recorded as owner + member so owner-gated mutations
    # and ESPN read gating pass by default (backend/league-authorization).
    owner = getattr(context, "default_user", "owner_user")
    if not get_item(context, f"LEAGUE#{canonical}", "METADATA"):
        put_item(
            context,
            {
                "PK": f"LEAGUE#{canonical}",
                "SK": "METADATA",
                "platform": platform,
                "league_name": "Test League",
                "owner_user_id": owner,
                "members": {owner},
            },
        )


@when('I GET "{path}"')
def step_get(context, path):
    context.response = context.api.get(path)


@when('I DELETE "{path}"')
def step_delete(context, path):
    context.response = context.api.delete(path)


@then("the API responds with status {code:d}")
def step_assert_status(context, code):
    assert context.response.status_code == code, (
        f"expected {code}, got {context.response.status_code}: {context.response.text}"
    )


@then('the API response detail is "{text}"')
def step_assert_detail(context, text):
    assert context.response.json()["detail"] == text, context.response.text


@then('the API response detail contains "{text}"')
def step_assert_detail_contains(context, text):
    assert text in context.response.json().get("detail", ""), context.response.text
