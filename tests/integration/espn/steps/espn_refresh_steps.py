import time
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from behave import given, then, when


@given("an ESPN league exists in DynamoDB")
def step_verify_league(context):
    resp = context.dynamodb_client.get_item(
        TableName=context.table_name,
        Key={
            "PK": {"S": f"LEAGUE#{context.test_league_id}#PLATFORM#ESPN"},
            "SK": {"S": "LEAGUE_LOOKUP"},
        },
    )
    item = resp.get("Item")
    assert item, (
        f"Precondition failed: LEAGUE_LOOKUP for {context.test_league_id} not found in DynamoDB"
    )
    context.test_canonical_id = item["canonical_league_id"]["S"]


@when("the onboarder Lambda handler is invoked with an ESPN REFRESH request")
def step_invoke_refresh(context):
    mock_ctx = MagicMock()
    mock_ctx.aws_request_id = "integration-test-espn-refresh-request-id"
    mock_ctx.function_name = "onboarder-integration-test"
    context.test_correlation_id = str(uuid.uuid4())
    event = {
        "requestType": "REFRESH",
        "correlation_id": context.test_correlation_id,
        "canonicalLeagueId": context.test_canonical_id,
        "body": {
            "leagueId": context.test_league_id,
            "platform": "ESPN",
            # ESPN refreshes must use the user-entered latest season, not the
            # previously-onboarded season (see backend/league-refresh / ESPN refresh season bug).
            "season": context.espn_season,
            "s2": context.espn_s2,
            "swid": context.espn_swid,
        },
    }
    context.response = context.onboarder_handler_mod.lambda_handler(event, mock_ctx)
    context.invoke_time = datetime.now(timezone.utc)


@then("the last_refresh_at on the test league is updated within 5 minutes")
def step_poll_last_refresh_at(context):
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
