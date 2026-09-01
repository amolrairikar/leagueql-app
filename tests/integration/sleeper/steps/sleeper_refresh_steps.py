import json
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from behave import given, then, when


def _test_league_current_season(context) -> str:
    """The test league's newest onboarded season, so the mocked NFL season is not
    behind it — the refresher skips any league whose newest onboarded season is
    behind the current NFL season. Using the calendar year would break off-season
    (e.g. an Aug run before the new season starts, when the league's newest season
    is still the prior year). Falls back to the current UTC year when the league is
    not yet onboarded (the 'a Sleeper league exists in DynamoDB' step then fails)."""
    resp = context.dynamodb_client.get_item(
        TableName=context.table_name,
        Key={
            "PK": {"S": f"LEAGUE#{context.test_league_id}#PLATFORM#SLEEPER"},
            "SK": {"S": "LEAGUE_LOOKUP"},
        },
    )
    seasons = resp.get("Item", {}).get("seasons", {}).get("SS")
    if seasons:
        return max(seasons, key=int)
    return str(datetime.now(timezone.utc).year)


@given("the NFL state API returns week {week:d} of the regular season")
def step_nfl_state_week(context, week):
    context.nfl_patcher = patch(
        "sleeper_refresh.handler.get_nfl_state",
        return_value={
            "season_type": "regular",
            "week": week,
            "season": _test_league_current_season(context),
        },
    )
    context.nfl_patcher.start()


@given("the NFL state API returns off-season")
def step_nfl_state_offseason(context):
    context.nfl_patcher = patch(
        "sleeper_refresh.handler.get_nfl_state",
        return_value={"season_type": "off", "week": 0},
    )
    context.nfl_patcher.start()


@given("a Sleeper league exists in DynamoDB")
def step_verify_league(context):
    resp = context.dynamodb_client.get_item(
        TableName=context.table_name,
        Key={
            "PK": {"S": f"LEAGUE#{context.test_league_id}#PLATFORM#SLEEPER"},
            "SK": {"S": "LEAGUE_LOOKUP"},
        },
    )
    item = resp.get("Item")
    assert item, (
        f"Precondition failed: LEAGUE_LOOKUP for {context.test_league_id} not found in DynamoDB"
    )
    context.test_canonical_id = item["canonical_league_id"]["S"]


@when("the sleeper refresh Lambda handler is invoked")
def step_invoke_handler(context):
    mock_ctx = MagicMock()
    mock_ctx.aws_request_id = "integration-test-request-id"
    mock_ctx.function_name = "sleeper-refresh-integration-test"
    context.response = context.handler_mod.lambda_handler({}, mock_ctx)
    context.invoke_time = datetime.now(timezone.utc)
    if hasattr(context, "nfl_patcher"):
        context.nfl_patcher.stop()


@then('the handler returns statusCode {code:d} with status "{expected_status}"')
def step_assert_response(context, code, expected_status):
    assert context.response["statusCode"] == code
    body = json.loads(context.response["body"])
    assert body["status"] == expected_status


@then("the last_refresh_at on the test league is updated within 5 minutes")
def step_poll_last_refresh_at(context):
    # Job status now lives in the JOB_STATUS item keyed by the correlation_id the
    # refresh handler generates internally (not observable here), so the
    # processor-written last_refresh_at on METADATA is the completion signal.
    deadline = datetime.now(timezone.utc) + timedelta(minutes=5)
    while datetime.now(timezone.utc) < deadline:
        resp = context.dynamodb_client.get_item(
            TableName=context.table_name,
            Key={
                "PK": {"S": f"LEAGUE#{context.test_canonical_id}"},
                "SK": {"S": "METADATA"},
            },
        )
        item = resp.get("Item", {})
        last_refresh_at = item.get("last_refresh_at", {}).get("S")
        if last_refresh_at:
            refresh_dt = datetime.fromisoformat(last_refresh_at)
            # Only accept a value freshly written by this invocation's refresh.
            if refresh_dt >= context.invoke_time - timedelta(seconds=5):
                return
        time.sleep(5)
    raise AssertionError(
        "last_refresh_at was not updated on the METADATA record within 5 minutes "
        "of the refresh invocation"
    )
