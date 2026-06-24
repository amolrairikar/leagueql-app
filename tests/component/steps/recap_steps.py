"""Steps for the AI weekly matchup recap generator component test (BE-022)."""

from unittest.mock import patch

from behave import given, then, when
from boto3.dynamodb.conditions import Key
from common_steps import get_item, put_item


def _matchup(week2: str) -> dict:
    """One minimal normal matchup row (ints only — the resource Table rejects float)."""
    return {
        "team_a_id": "1",
        "team_a_display_name": "alice",
        "team_a_team_name": "Alice's Team",
        "team_a_score": 120,
        "team_a_starters": [
            {"full_name": "QB One", "position": "QB", "points_scored": 30},
        ],
        "team_a_bench": [],
        "team_b_id": "2",
        "team_b_display_name": "bob",
        "team_b_team_name": "Bob's Team",
        "team_b_score": 90,
        "team_b_starters": [],
        "team_b_bench": [],
        "playoff_round": None,
        "winner": "1",
        "loser": "2",
        "week": week2,
        "season": "0000",
    }


def _seed_season(context, canonical: str, season: str, weeks: list[str]) -> None:
    for week2 in weeks:
        put_item(
            context,
            {
                "PK": f"LEAGUE#{canonical}",
                "SK": f"MATCHUPS#{season}#WEEK#{week2}",
                "data": [_matchup(week2)],
            },
        )
    put_item(
        context,
        {
            "PK": f"LEAGUE#{canonical}",
            "SK": f"STANDINGS#{season}",
            "data": [
                {"team_id": "1", "record": "1-0-0"},
                {"team_id": "2", "record": "0-1-0"},
            ],
        },
    )


@given('a premium league "{canonical}" with matchups for seasons "{seasons}"')
def step_seed_premium_league(context, canonical, seasons):
    season_list = [s.strip() for s in seasons.split(",")]
    # LEAGUE_LOOKUP carries the seasons set read via GSI1 for season enumeration.
    put_item(
        context,
        {
            "PK": "LEAGUE#100#PLATFORM#SLEEPER",
            "SK": "LEAGUE_LOOKUP",
            "canonical_league_id": canonical,
            "seasons": set(season_list),
            "platform": "SLEEPER",
            "league_id": "100",
        },
    )
    # Premium METADATA (far-future subscription) so the server-side gate passes.
    put_item(
        context,
        {
            "PK": f"LEAGUE#{canonical}",
            "SK": "METADATA",
            "platform": "SLEEPER",
            "league_name": "Recap League",
            "subscription_end_time": "2999-01-01T00:00:00+00:00",
        },
    )
    # First two seasons get 2 weeks / 1 week so "all weeks of all seasons" is
    # meaningfully exercised; extra seasons (if any) get a single week.
    for i, season in enumerate(season_list):
        weeks = ["01", "02"] if i == 0 else ["01"]
        _seed_season(context, canonical, season, weeks)


def _ensure_recap_spy(context):
    """Patch the recap Lambda's Bedrock call with a counting spy (once per scenario)."""
    if getattr(context, "recap_gen_spy", None) is None:
        patcher = patch.object(
            context.recap_handler,
            "generate_recap",
            return_value={"headline": "Big Week", "body": "Para one.\n\nPara two."},
        )
        context.recap_gen_spy = patcher.start()
        context._patches.append(patcher)


@when('the recap generator runs for league "{canonical}" on "{platform}"')
def step_run_recap(context, canonical, platform):
    _ensure_recap_spy(context)
    context.recap_gen_spy.reset_mock()  # scope assertions to this run
    context.recap_response = context.recap_handler.lambda_handler(
        {"canonical_league_id": canonical, "platform": platform}, None
    )


@given('the recap generator has already run for league "{canonical}" on "{platform}"')
def step_recap_already_ran(context, canonical, platform):
    _ensure_recap_spy(context)
    context.recap_handler.lambda_handler(
        {"canonical_league_id": canonical, "platform": platform}, None
    )


@then(
    'a MATCHUP_RECAP item exists for league "{canonical}" season "{season}" '
    'week "{week2}"'
)
def step_recap_item_exists(context, canonical, season, week2):
    item = get_item(
        context, f"LEAGUE#{canonical}", f"MATCHUP_RECAP#{season}#WEEK#{week2}"
    )
    assert item, f"no recap item for {season} week {week2}"
    recap = item["data"][0]
    assert recap["headline"], "recap headline missing"
    assert recap["body"], "recap body missing"
    assert recap["model"] == "us.anthropic.claude-haiku-4-5-20251001-v1:0"


@then('no MATCHUP_RECAP items exist for league "{canonical}"')
def step_no_recap_items(context, canonical):
    table = context.ddb_resource.Table(context.table_name)
    resp = table.query(
        KeyConditionExpression=Key("PK").eq(f"LEAGUE#{canonical}")
        & Key("SK").begins_with("MATCHUP_RECAP#")
    )
    assert not resp.get("Items"), "expected no recap items"


@then("the recap model generated {count:d} recaps")
def step_recap_model_count(context, count):
    assert context.recap_gen_spy.call_count == count, (
        f"expected {count} generation(s), got {context.recap_gen_spy.call_count}"
    )


@then("the recap generator was invoked after processing")
def step_recap_invoked_after_processing(context):
    # BE-022: the processor fires the recap-generator Lambda at end of run (the
    # shared invoke spy stands in for the absent moto Lambda service).
    assert context.recap_lambda_client.invoke.called, (
        "recap generator was not invoked at end of processing"
    )
