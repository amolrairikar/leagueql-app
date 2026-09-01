"""Steps for the scheduled Sleeper auto-refresh Lambda (backend/scheduled-sleeper-auto-refresh)."""

import json
from unittest.mock import MagicMock, patch

from behave import given, then, when
from common_steps import put_item


@given(
    'an onboarded Sleeper league "{league_id}" canonical "{canonical}" season "{season}"'
)
def step_seed_sleeper_league(context, league_id, canonical, season):
    put_item(
        context,
        {
            "PK": f"LEAGUE#{league_id}#PLATFORM#SLEEPER",
            "SK": "LEAGUE_LOOKUP",
            "canonical_league_id": canonical,
            "seasons": {season},
            "platform": "SLEEPER",
            "league_id": league_id,
        },
    )


@given(
    'a pending Sleeper renewal "{league_id}" canonical "{canonical}" pending season "{season}"'
)
def step_seed_pending_renewal(context, league_id, canonical, season):
    put_item(
        context,
        {
            "PK": f"LEAGUE#{league_id}#PLATFORM#SLEEPER",
            "SK": "LEAGUE_LOOKUP",
            "canonical_league_id": canonical,
            "pending_season": season,
            "platform": "SLEEPER",
            "league_id": league_id,
        },
    )


@given('an onboarded ESPN league "{league_id}" canonical "{canonical}"')
def step_seed_espn_league(context, league_id, canonical):
    put_item(
        context,
        {
            "PK": f"LEAGUE#{league_id}#PLATFORM#ESPN",
            "SK": "LEAGUE_LOOKUP",
            "canonical_league_id": canonical,
            "seasons": {"2024"},
            "platform": "ESPN",
            "league_id": league_id,
        },
    )


@when(
    'the auto-refresh runs with NFL state season_type "{season_type}" week "{week:d}"'
)
def step_run_refresh(context, season_type, week):
    _run_refresh(context, season_type, week, "2024")


@when(
    'the auto-refresh runs with NFL state season_type "{season_type}" week "{week:d}" season "{season}"'
)
def step_run_refresh_with_season(context, season_type, week, season):
    _run_refresh(context, season_type, week, season)


def _run_refresh(context, season_type, week, season):
    nfl_state = {"season_type": season_type, "season": season, "week": week}
    state_patch = patch.object(
        context.refresh_handler, "get_nfl_state", MagicMock(return_value=nfl_state)
    )
    state_patch.start()
    context._patches.append(state_patch)

    invoke = MagicMock()
    invoke_patch = patch.object(
        context.refresh_handler, "invoke_onboarder_lambda", invoke
    )
    context.invoke_mock = invoke_patch.start()
    context._patches.append(invoke_patch)

    ctx = MagicMock(aws_request_id="req", function_name="sleeper-refresh-test")
    context.refresh_response = context.refresh_handler.lambda_handler({}, ctx)


@then('the auto-refresh response status is "{status}"')
def step_refresh_status(context, status):
    body = json.loads(context.refresh_response["body"])
    assert body["status"] == status, body


@then("the onboarder was invoked {count:d} time(s)")
def step_invoke_count(context, count):
    assert context.invoke_mock.call_count == count, (
        f"expected {count} invokes, got {context.invoke_mock.call_count}"
    )


@then('the onboarder was invoked for league "{league_id}"')
def step_invoke_for(context, league_id):
    called = [c.args[0] for c in context.invoke_mock.call_args_list]
    assert league_id in called, f"invoked for {called}, not {league_id}"
