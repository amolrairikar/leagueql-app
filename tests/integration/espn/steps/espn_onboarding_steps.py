import json
import time
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from behave import then, when


@when("the onboarder Lambda handler is invoked with an ESPN ONBOARD request")
def step_invoke_onboarder(context):
    mock_ctx = MagicMock()
    mock_ctx.aws_request_id = "integration-test-espn-onboard-request-id"
    mock_ctx.function_name = "onboarder-integration-test"
    # Pass a known correlation_id so we can poll the JOB_STATUS item the processor
    # upserts (status now lives there, keyed by correlation_id, not on METADATA).
    context.test_correlation_id = str(uuid.uuid4())
    event = {
        "requestType": "ONBOARD",
        "correlation_id": context.test_correlation_id,
        # Record the test user as owner so the league mirrors a real API onboard
        # and the owner-gated cleanup DELETE (same user) succeeds (BE-016).
        "ownerUserId": context.clerk_user_id,
        "body": {
            "leagueId": context.test_league_id,
            "platform": "ESPN",
            "season": context.espn_season,
            "s2": context.espn_s2,
            "swid": context.espn_swid,
        },
    }
    context.response = context.onboarder_handler_mod.lambda_handler(event, mock_ctx)
    body = json.loads(context.response["body"])
    context.test_canonical_id = body.get("canonical_league_id")


# Shared by the onboarding and refresh features (both run in this steps registry).
@then('the handler returns statusCode {code:d} with status "{expected_status}"')
def step_assert_response(context, code, expected_status):
    assert context.response["statusCode"] == code
    body = json.loads(context.response["body"])
    assert body["status"] == expected_status


# Shared by the onboarding and refresh features.
@then('DynamoDB shows job status "{expected}" for the test league')
def step_poll_job_status(context, expected):
    deadline = datetime.now(timezone.utc) + timedelta(minutes=5)
    while datetime.now(timezone.utc) < deadline:
        resp = context.dynamodb_client.get_item(
            TableName=context.table_name,
            Key={
                "PK": {"S": f"JOB#{context.test_correlation_id}"},
                "SK": {"S": "JOB_STATUS"},
            },
        )
        item = resp.get("Item", {})
        if item.get("status", {}).get("S") == expected:
            return
        time.sleep(5)
    raise AssertionError(
        f"job status '{expected}' not seen on JOB_STATUS record within 5 minutes"
    )


@then("the LEAGUE_LOOKUP record exists in DynamoDB for the test league")
def step_assert_league_lookup(context):
    resp = context.dynamodb_client.get_item(
        TableName=context.table_name,
        Key={
            "PK": {"S": f"LEAGUE#{context.test_league_id}#PLATFORM#ESPN"},
            "SK": {"S": "LEAGUE_LOOKUP"},
        },
    )
    item = resp.get("Item")
    assert item, (
        f"LEAGUE_LOOKUP for {context.test_league_id} not found in DynamoDB after onboarding"
    )
    assert item.get("canonical_league_id", {}).get("S") == context.test_canonical_id
