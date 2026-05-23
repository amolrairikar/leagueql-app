import json
from unittest.mock import MagicMock, patch

from behave import given, then, when

PLAYER_METADATA_S3_KEY = "player-metadata/sleeper_nfl_players.json"
REQUIRED_PLAYER_FIELDS = {"first_name", "last_name", "position"}


@given("the NFL state API returns off-season")
def step_nfl_state_offseason(context):
    context.nfl_patcher = patch(
        "player_metadata.handler.fetch_nfl_state",
        return_value={"season_type": "off", "week": 0},
    )
    context.nfl_patcher.start()


@given("the NFL state API returns week 5 of the regular season")
def step_nfl_state_regular(context):
    context.nfl_patcher = patch(
        "player_metadata.handler.fetch_nfl_state",
        return_value={"season_type": "regular", "week": 5},
    )
    context.nfl_patcher.start()


@when("the player metadata Lambda handler is invoked")
def step_invoke_handler(context):
    mock_ctx = MagicMock()
    mock_ctx.aws_request_id = "integration-test-player-metadata-request-id"
    mock_ctx.function_name = "player-metadata-integration-test"
    context.response = context.handler_mod.lambda_handler({}, mock_ctx)
    if hasattr(context, "nfl_patcher"):
        context.nfl_patcher.stop()


@then("the handler returns without error")
def step_assert_no_error(context):
    assert context.response is None


@then("player metadata is written to S3 with valid player records")
def step_assert_s3_write(context):
    obj = context.s3_client.get_object(
        Bucket=context.s3_bucket, Key=PLAYER_METADATA_S3_KEY
    )
    players_data = json.loads(obj["Body"].read())
    assert isinstance(players_data, dict) and players_data, (
        "Expected non-empty dict of player records in S3"
    )
    sample = list(players_data.values())[:10]
    for player in sample:
        missing = REQUIRED_PLAYER_FIELDS - set(player.keys())
        assert not missing, f"Player record missing fields {missing}: {player}"
