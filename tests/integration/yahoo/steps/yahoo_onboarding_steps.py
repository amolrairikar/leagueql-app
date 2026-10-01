import json
import time
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from behave import then, when


@when("the onboarder Lambda handler is invoked with a Yahoo ONBOARD request")
def step_invoke_onboarder(context):
    mock_ctx = MagicMock()
    mock_ctx.aws_request_id = "integration-test-yahoo-onboard-request-id"
    mock_ctx.function_name = "onboarder-integration-test"
    # Pass a known correlation_id so we can poll the JOB_STATUS item the processor
    # upserts (status now lives there, keyed by correlation_id, not on METADATA).
    context.test_correlation_id = str(uuid.uuid4())
    event = {
        "requestType": "ONBOARD",
        "correlation_id": context.test_correlation_id,
        # Yahoo has no cookies: the onboarder resolves the owner's linked Yahoo token
        # from this Clerk id (backend/yahoo-oauth). Recording the test user as owner also
        # lets the owner-gated cleanup DELETE (same user) succeed (backend/league-authorization).
        "ownerUserId": context.clerk_user_id,
        "body": {"leagueId": context.test_league_id, "platform": "YAHOO"},
    }
    context.response = context.onboarder_handler_mod.lambda_handler(event, mock_ctx)
    body = json.loads(context.response["body"])
    context.test_canonical_id = body.get("canonical_league_id")


@then('the handler returns statusCode {code:d} with status "{expected_status}"')
def step_assert_response(context, code, expected_status):
    assert context.response["statusCode"] == code, context.response
    body = json.loads(context.response["body"])
    assert body["status"] == expected_status


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
            "PK": {"S": f"LEAGUE#{context.test_league_id}#PLATFORM#YAHOO"},
            "SK": {"S": "LEAGUE_LOOKUP"},
        },
    )
    item = resp.get("Item")
    assert item, (
        f"LEAGUE_LOOKUP for {context.test_league_id} not found in DynamoDB after onboarding"
    )
    assert item.get("canonical_league_id", {}).get("S") == context.test_canonical_id
    # Every onboarded Yahoo season starts lineup-pending and the backfill works newest-first;
    # the backfill steps wait on just this season so the wait stays bounded however many
    # older seasons the league has. Taken from LEAGUE_LOOKUP, not pending_lineup_seasons,
    # since a small backfill may already have cleared it.
    context.newest_season = max(item["seasons"]["SS"], key=int)


def _metadata(context) -> dict:
    resp = context.dynamodb_client.get_item(
        TableName=context.table_name,
        Key={
            "PK": {"S": f"LEAGUE#{context.test_canonical_id}"},
            "SK": {"S": "METADATA"},
        },
        ConsistentRead=True,
    )
    return resp.get("Item", {})


@then("the lineup backfill completes the newest season within {minutes:d} minutes")
def step_poll_backfill_complete(context, minutes):
    season = context.newest_season
    deadline = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    while datetime.now(timezone.utc) < deadline:
        item = _metadata(context)
        failed = item.get("failed_lineup_seasons", {}).get("SS", [])
        assert season not in failed, (
            f"lineup backfill marked season {season} failed (revoked link / no access / "
            "retries exhausted) — check the leagueql-yahoo-lineup-backfill logs"
        )
        if season not in item.get("pending_lineup_seasons", {}).get("SS", []):
            return
        time.sleep(10)
    raise AssertionError(
        f"season {season} still lineup-pending after {minutes} minutes; if Yahoo "
        "throttled the backfill (999), its retry is queued ~15 minutes out"
    )


@then(
    "the processor attaches lineups to the newest season's matchups within {minutes:d} minutes"
)
def step_poll_matchup_lineups(context, minutes):
    season = context.newest_season
    store_key = f"raw-api-data/{context.test_canonical_id}/yahoo_rosters/{season}.json"
    store = json.loads(
        context.s3_client.get_object(Bucket=context.s3_bucket, Key=store_key)[
            "Body"
        ].read()
    )
    assert store["weeks"], f"lineup store {store_key} has no weeks"
    week = min(store["weeks"], key=int)
    # Completion re-triggers the processor via the manifest; its rebuild is asynchronous.
    deadline = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    while datetime.now(timezone.utc) < deadline:
        resp = context.dynamodb_client.get_item(
            TableName=context.table_name,
            Key={
                "PK": {"S": f"LEAGUE#{context.test_canonical_id}"},
                "SK": {"S": f"MATCHUPS#{season}#WEEK#{int(week):02d}"},
            },
        )
        rows = resp.get("Item", {}).get("data", {}).get("L", [])
        if any(row["M"].get("team_a_starters", {}).get("L") for row in rows):
            return
        time.sleep(10)
    raise AssertionError(
        f"MATCHUPS#{season}#WEEK#{int(week):02d} has no starters {minutes} minutes "
        "after the backfill completed"
    )
