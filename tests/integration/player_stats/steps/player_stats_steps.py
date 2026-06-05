import datetime
import json

from behave import given, then, when

PLAYER_METADATA_S3_KEY = "player-metadata/sleeper_nfl_players.json"
PLAYER_STATS_S3_KEY = "player-stats/sleeper_nfl_player_stats.json"
# Isolated key so a capped test run never clobbers the production stats cache.
TEST_OUTPUT_S3_KEY = "player-stats/integration-test/sleeper_nfl_player_stats.json"
MAX_PLAYERS = 100


def _most_recent_completed_season() -> str:
    # The NFL regular season runs Sep–Jan. Before September the most recent
    # completed season is the previous calendar year; otherwise it is the
    # current year.
    today = datetime.date.today()
    return str(today.year if today.month >= 9 else today.year - 1)


def _production_cache_fingerprint(context) -> tuple | None:
    # (ETag, ContentLength) of the live stats cache, or None if it does not
    # exist. Used to prove the capped run leaves the production object untouched.
    try:
        head = context.s3_client.head_object(
            Bucket=context.s3_bucket, Key=PLAYER_STATS_S3_KEY
        )
        return (head["ETag"], head["ContentLength"])
    except context.s3_client.exceptions.ClientError:
        return None


@given(
    "an S3 event notification for the player metadata object with season, player-cap, and output-key overrides"
)
def step_build_event(context):
    context.season = _most_recent_completed_season()
    context.test_output_key = TEST_OUTPUT_S3_KEY
    # Snapshot the production cache so we can assert it is untouched afterward.
    context.prod_cache_fingerprint = _production_cache_fingerprint(context)
    # Mirror the S3 ObjectCreated event AWS delivers when the player metadata
    # object is written, plus overrides that drive a deterministic, capped
    # refresh into an isolated test key regardless of the live NFL state.
    context.invoke_payload = {
        "season": context.season,
        "max_players": MAX_PLAYERS,
        "output_key": TEST_OUTPUT_S3_KEY,
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


@then(
    "player stats for that season are written to the isolated test key for the active players"
)
def step_assert_s3(context):
    obj = context.s3_client.get_object(
        Bucket=context.s3_bucket, Key=context.test_output_key
    )
    stats_data = json.loads(obj["Body"].read())
    assert isinstance(stats_data, dict) and stats_data, (
        "Expected a non-empty dict of player stats at the test key"
    )
    # A capped run resolves stats for at most MAX_PLAYERS, and some of the first
    # N active players legitimately have no stats (404), so assert a sane range
    # rather than an exact count.
    assert 1 <= len(stats_data) <= MAX_PLAYERS, (
        f"Expected between 1 and {MAX_PLAYERS} players, got {len(stats_data)}"
    )
    for player_id, seasons in stats_data.items():
        assert context.season in seasons, (
            f"Player {player_id} missing season {context.season}: {seasons}"
        )
        assert isinstance(seasons[context.season], dict), (
            f"Player {player_id} season stats not a dict: {seasons[context.season]}"
        )


@then("the production player stats cache is left untouched")
def step_assert_prod_untouched(context):
    after = _production_cache_fingerprint(context)
    assert after == context.prod_cache_fingerprint, (
        "Production stats cache changed during a capped test run: "
        f"before={context.prod_cache_fingerprint} after={after}"
    )
