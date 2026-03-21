import base64
import json
import os

import boto3
from behave import given, when, then, use_step_matcher
from behave.runner import Context
from dotenv import load_dotenv

use_step_matcher("re")


@given(r"a (valid|invalid) set of (.+) league inputs")  # type: ignore[reportCallIssue]
def step_given_valid_espn_league_inputs(
    context: Context, input_validity: str, platform: str
):
    load_dotenv()

    if input_validity == "valid":
        if platform == "ESPN":
            context.league_id = "1770206"
            context.platform = platform
            context.season = os.environ["SEASON"]
            context.s2 = os.environ["S2"]
            context.swid = os.environ["SWID"]
            context.lambda_payload = {
                "name": "test-event",
                "body": {
                    "leagueId": context.league_id,
                    "platform": context.platform,
                    "season": context.season,
                    "swid": context.swid,
                    "s2": context.s2,
                },
            }
        else:
            context.league_id = "1251587932842627072"
            context.platform = platform
            context.season = os.environ["SEASON"]
            context.lambda_payload = {
                "name": "test-event",
                "body": {
                    "leagueId": context.league_id,
                    "platform": context.platform,
                },
            }
    else:
        if platform == "ESPN":
            context.league_id = "invalid"
            context.platform = platform
            context.season = os.environ["SEASON"]
            context.s2 = os.environ["S2"]
            context.swid = os.environ["SWID"]
            context.lambda_payload = {
                "name": "test-event",
                "body": {
                    "leagueId": context.league_id,
                    "platform": context.platform,
                    "season": context.season,
                    "swid": context.swid,
                    "s2": context.s2,
                },
            }
        else:
            context.league_id = "invalid"
            context.platform = platform
            context.season = os.environ["SEASON"]
            context.lambda_payload = {
                "name": "test-event",
                "body": {
                    "leagueId": context.league_id,
                    "platform": context.platform,
                },
            }
    context.lambda_client_context = base64.b64encode(
        json.dumps({}).encode("utf-8")
    ).decode("utf-8")


@when("we run the onboarding lambda")  # type: ignore[reportCallIssue]
def step_run_onboarding_lambda(context: Context):
    client = boto3.client("lambda")

    response = client.invoke(
        FunctionName="fantasy-football-recap-onboarder-dev-east",
        InvocationType="RequestResponse",
        Payload=json.dumps(getattr(context, "lambda_payload", {})),
        ClientContext=context.lambda_client_context,
    )

    payload_bytes = response["Payload"].read()
    raw_payload = json.loads(payload_bytes)
    context.lambda_response = {
        "status_code": raw_payload["statusCode"],
        "body": json.loads(raw_payload["body"]),
    }


@then("the lambda will complete successfully")  # type: ignore[reportCallIssue]
def step_lambda_completes_successfully(context: Context):
    assert "FunctionError" not in context.lambda_response, (
        f"Lambda function error: {context.lambda_response['payload']}"
    )


@then(r"the lambda response object status code will be (\d+)")  # type: ignore[reportCallIssue]
def step_lambda_status_code_200(context: Context, status_code: str):
    expected = int(status_code)
    actual = context.lambda_response["status_code"]
    assert actual == expected, f"Expected status code {expected}, got {actual}"


@then("the DynamoDB table will contain (\d+) items")  # type: ignore[reportCallIssue]
def step_dynamodb_table_contains_3_items(context: Context, item_count: str):
    expected = int(item_count)
    dynamodb = boto3.client("dynamodb")
    response = dynamodb.scan(
        TableName="fantasy-football-recap-table-dev",
        Select="COUNT",
    )
    actual = response["Count"]
    assert actual == expected, f"Expected {expected} items in DynamoDB, got {actual}"
