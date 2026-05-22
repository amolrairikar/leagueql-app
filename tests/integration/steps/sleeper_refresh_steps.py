import json
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from behave import given, then, when


@given("the NFL state API returns week {week:d} of the regular season")
def step_nfl_state_week(context, week):
    context.nfl_patcher = patch(
        "sleeper_refresh.handler.get_nfl_state",
        return_value={"season_type": "regular", "week": week},
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


@then('DynamoDB shows refresh_status "{expected}" for the test league')
def step_poll_refresh_status(context, expected):
    deadline = datetime.now(timezone.utc) + timedelta(minutes=3)
    while datetime.now(timezone.utc) < deadline:
        resp = context.dynamodb_client.get_item(
            TableName=context.table_name,
            Key={
                "PK": {"S": f"LEAGUE#{context.test_canonical_id}"},
                "SK": {"S": "METADATA"},
            },
        )
        item = resp.get("Item", {})
        if item.get("refresh_status", {}).get("S") == expected:
            context.last_refresh_at = item.get("last_refresh_at", {}).get("S")
            return
        time.sleep(5)
    raise AssertionError(
        f"refresh_status '{expected}' not seen on METADATA record within 3 minutes"
    )


@then("the last_refresh_at is within 5 minutes of the current time")
def step_assert_last_refresh_at(context):
    assert context.last_refresh_at, "last_refresh_at not set on METADATA record"
    refresh_dt = datetime.fromisoformat(context.last_refresh_at)
    now = datetime.now(timezone.utc)
    assert refresh_dt >= context.invoke_time - timedelta(seconds=5), (
        f"last_refresh_at ({refresh_dt}) predates the handler invocation ({context.invoke_time})"
    )
    assert now - refresh_dt < timedelta(minutes=5), (
        f"last_refresh_at is {now - refresh_dt} old (> 5 minutes)"
    )
