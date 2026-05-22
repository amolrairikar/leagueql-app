import json
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from behave import then, when


@when("the onboarder Lambda handler is invoked with an ONBOARD request")
def step_invoke_onboarder(context):
    mock_ctx = MagicMock()
    mock_ctx.aws_request_id = "integration-test-onboard-request-id"
    mock_ctx.function_name = "onboarder-integration-test"
    event = {
        "requestType": "ONBOARD",
        "body": {"leagueId": context.test_league_id, "platform": "SLEEPER"},
    }
    context.response = context.onboarder_handler_mod.lambda_handler(event, mock_ctx)
    body = json.loads(context.response["body"])
    context.test_canonical_id = body.get("canonical_league_id")


@then('DynamoDB shows onboarding_status "{expected}" for the test league')
def step_poll_onboarding_status(context, expected):
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
        if item.get("onboarding_status", {}).get("S") == expected:
            return
        time.sleep(5)
    raise AssertionError(
        f"onboarding_status '{expected}' not seen on METADATA record within 3 minutes"
    )


@then("the LEAGUE_LOOKUP record exists in DynamoDB for the test league")
def step_assert_league_lookup(context):
    resp = context.dynamodb_client.get_item(
        TableName=context.table_name,
        Key={
            "PK": {"S": f"LEAGUE#{context.test_league_id}#PLATFORM#SLEEPER"},
            "SK": {"S": "LEAGUE_LOOKUP"},
        },
    )
    item = resp.get("Item")
    assert item, (
        f"LEAGUE_LOOKUP for {context.test_league_id} not found in DynamoDB after onboarding"
    )
    assert item.get("canonical_league_id", {}).get("S") == context.test_canonical_id
