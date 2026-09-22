"""Steps for the scheduled league auto-refresh Lambda (backend/scheduled-league-auto-refresh)."""

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
    # No METADATA / opt-in flag: an ESPN league not enrolled in auto-refresh.
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


@given(
    'an auto-refresh ESPN league "{league_id}" canonical "{canonical}" season "{season}" owner "{owner}"'
)
def step_seed_espn_league_optin(context, league_id, canonical, season, owner):
    # An ESPN league opted into auto-refresh: LEAGUE_LOOKUP + METADATA with owner and the flag.
    put_item(
        context,
        {
            "PK": f"LEAGUE#{league_id}#PLATFORM#ESPN",
            "SK": "LEAGUE_LOOKUP",
            "canonical_league_id": canonical,
            "seasons": {season},
            "platform": "ESPN",
            "league_id": league_id,
        },
    )
    put_item(
        context,
        {
            "PK": f"LEAGUE#{canonical}",
            "SK": "METADATA",
            "platform": "ESPN",
            "owner_user_id": owner,
            "auto_refresh_enabled": True,
        },
    )


@given(
    'an onboarded Yahoo league "{league_id}" canonical "{canonical}" season "{season}" owner "{owner}"'
)
def step_seed_yahoo_league(context, league_id, canonical, season, owner):
    put_item(
        context,
        {
            "PK": f"LEAGUE#{league_id}#PLATFORM#YAHOO",
            "SK": "LEAGUE_LOOKUP",
            "canonical_league_id": canonical,
            "seasons": {season},
            "platform": "YAHOO",
            "league_id": league_id,
        },
    )
    # Yahoo auto-refresh is opt-in; this seeds an opted-in league.
    put_item(
        context,
        {
            "PK": f"LEAGUE#{canonical}",
            "SK": "METADATA",
            "platform": "YAHOO",
            "owner_user_id": owner,
            "auto_refresh_enabled": True,
        },
    )


@given(
    'a not-opted-in Yahoo league "{league_id}" canonical "{canonical}" season "{season}" owner "{owner}"'
)
def step_seed_yahoo_league_not_opted_in(context, league_id, canonical, season, owner):
    put_item(
        context,
        {
            "PK": f"LEAGUE#{league_id}#PLATFORM#YAHOO",
            "SK": "LEAGUE_LOOKUP",
            "canonical_league_id": canonical,
            "seasons": {season},
            "platform": "YAHOO",
            "league_id": league_id,
        },
    )
    # METADATA has an owner but no auto_refresh_enabled flag → opt-in required, not refreshed.
    put_item(
        context,
        {
            "PK": f"LEAGUE#{canonical}",
            "SK": "METADATA",
            "platform": "YAHOO",
            "owner_user_id": owner,
        },
    )


@given(
    'an onboarded Yahoo league "{league_id}" canonical "{canonical}" season "{season}" with no owner'
)
def step_seed_yahoo_league_no_owner(context, league_id, canonical, season):
    put_item(
        context,
        {
            "PK": f"LEAGUE#{league_id}#PLATFORM#YAHOO",
            "SK": "LEAGUE_LOOKUP",
            "canonical_league_id": canonical,
            "seasons": {season},
            "platform": "YAHOO",
            "league_id": league_id,
        },
    )
    # Opted in but no owner_user_id → cannot be refreshed without an owner, so skipped.
    put_item(
        context,
        {
            "PK": f"LEAGUE#{canonical}",
            "SK": "METADATA",
            "platform": "YAHOO",
            "auto_refresh_enabled": True,
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

    # Pacing sleeps between same-platform dispatches; no-op it so the run is fast.
    pace_patch = patch.object(context.refresh_handler, "pace_dispatch", MagicMock())
    pace_patch.start()
    context._patches.append(pace_patch)

    invoke = MagicMock()
    invoke_patch = patch.object(
        context.refresh_handler, "invoke_onboarder_lambda", invoke
    )
    context.invoke_mock = invoke_patch.start()
    context._patches.append(invoke_patch)

    ctx = MagicMock(aws_request_id="req", function_name="league-refresh-test")
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


@then('the onboarder was invoked for Yahoo league "{league_id}" with owner "{owner}"')
def step_invoke_for_with_owner(context, league_id, owner):
    match = [
        c
        for c in context.invoke_mock.call_args_list
        if c.args and c.args[0] == league_id
    ]
    assert match, f"onboarder not invoked for league {league_id}"
    call = match[0]
    assert call.kwargs.get("platform") == "YAHOO", call.kwargs
    assert call.kwargs.get("owner_user_id") == owner, call.kwargs


@then(
    'the onboarder was invoked for ESPN league "{league_id}" with owner "{owner}" and season "{season}"'
)
def step_invoke_for_espn(context, league_id, owner, season):
    match = [
        c
        for c in context.invoke_mock.call_args_list
        if c.args and c.args[0] == league_id
    ]
    assert match, f"onboarder not invoked for ESPN league {league_id}"
    call = match[0]
    assert call.kwargs.get("platform") == "ESPN", call.kwargs
    assert call.kwargs.get("owner_user_id") == owner, call.kwargs
    # ESPN dispatch carries the current season and NO cookies (the onboarder fetches the
    # owner's stored cookies itself, backend/scheduled-league-auto-refresh).
    assert call.kwargs.get("season") == season, call.kwargs
    assert "s2" not in call.kwargs and "swid" not in call.kwargs, call.kwargs
