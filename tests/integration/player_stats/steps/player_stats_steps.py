import datetime
import json

from behave import given, then, when

PLAYER_METADATA_S3_KEY = "player-metadata/sleeper_nfl_players.json"
PLAYER_STATS_S3_KEY = "player-stats/sleeper_nfl_player_stats.json"


def _most_recent_completed_season() -> str:
    # The NFL regular season runs Sep–Jan. Before September the most recent
    # completed season is the previous calendar year; otherwise it is the
    # current year.
    today = datetime.date.today()
    return str(today.year if today.month >= 9 else today.year - 1)


@given("an S3 event notification for the player metadata object with a season override")
def step_build_event(context):
    context.season = _most_recent_completed_season()
    # Mirror the S3 ObjectCreated event AWS delivers when the player metadata
    # object is written, plus a ``season`` override that drives a deterministic
    # full-season refresh regardless of the live (off-season) NFL state.
    context.invoke_payload = {
        "season": context.season,
        "Records": [
            {
                "eventVersion": "2.1",
                "eventSource": "aws:s3",
                "awsRegion": "us-east-1",
                "eventName": "ObjectCreated:Put",
                "s3": {
                    "s3SchemaVersion": "1.0",
                    "bucket": {
                        "name": context.s3_bucket,
                        "arn": f"arn:aws:s3:::{context.s3_bucket}",
                    },
                    "object": {"key": PLAYER_METADATA_S3_KEY},
                },
            }
        ],
    }


@when("the deployed player stats refresher Lambda is invoked synchronously")
def step_invoke_deployed(context):
    response = context.lambda_client.invoke(
        FunctionName=context.function_name,
        InvocationType="RequestResponse",
        Payload=json.dumps(context.invoke_payload).encode(),
    )
    context.invoke_status = response["StatusCode"]
    context.function_error = response.get("FunctionError")
    context.invoke_response_payload = response["Payload"].read().decode()


@then("the invocation succeeds without a function error")
def step_assert_invoke_ok(context):
    assert context.invoke_status == 200, (
        f"Unexpected status {context.invoke_status}: {context.invoke_response_payload}"
    )
    assert context.function_error is None, (
        f"Lambda returned a function error ({context.function_error}): "
        f"{context.invoke_response_payload}"
    )


@then("player stats for that season are written to S3 for the active players")
def step_assert_s3(context):
    obj = context.s3_client.get_object(
        Bucket=context.s3_bucket, Key=PLAYER_STATS_S3_KEY
    )
    stats_data = json.loads(obj["Body"].read())
    assert isinstance(stats_data, dict) and stats_data, (
        "Expected a non-empty dict of player stats in S3"
    )
    # A full-season refresh should resolve stats for many players, not a handful.
    assert len(stats_data) >= 100, (
        f"Expected stats for many players, got {len(stats_data)}"
    )
    for player_id, seasons in list(stats_data.items())[:10]:
        assert context.season in seasons, (
            f"Player {player_id} missing season {context.season}: {seasons}"
        )
        assert isinstance(seasons[context.season], dict), (
            f"Player {player_id} season stats not a dict: {seasons[context.season]}"
        )
