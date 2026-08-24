"""Steps for the player metadata refresher Lambda (backend/player-metadata-refresher).

The Sleeper HTTP boundary is mocked per scenario (NFL state via
``fetch_nfl_state``, the players endpoint via the module-level ``http_session``);
S3 is moto-backed, so the cache write is a real round-trip.
"""

import json
from unittest.mock import MagicMock, patch

from behave import given, then, when
from botocore.exceptions import ClientError

REQUIRED_PLAYER_FIELDS = {"first_name", "last_name", "position"}


def _patch_nfl_state(context, season_type):
    patcher = patch.object(
        context.player_metadata_handler,
        "fetch_nfl_state",
        MagicMock(return_value={"season_type": season_type, "week": 5}),
    )
    patcher.start()
    context._patches.append(patcher)


def _patch_players_response(context, payload):
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = payload
    mock_session = MagicMock()
    mock_session.get.return_value = mock_resp
    patcher = patch.object(
        context.player_metadata_handler, "http_session", mock_session
    )
    patcher.start()
    context._patches.append(patcher)


def _metadata_key(context):
    return context.player_metadata_handler.PLAYER_METADATA_S3_KEY


def _object_exists(context, key):
    try:
        context.s3.head_object(Bucket=context.bucket_name, Key=key)
        return True
    except ClientError:
        return False


@given("the NFL state is the regular season")
def step_state_regular(context):
    _patch_nfl_state(context, "regular")


@given("the NFL state is the offseason")
def step_state_offseason(context):
    _patch_nfl_state(context, "off")


@given("Sleeper returns a valid player metadata payload")
def step_valid_payload(context):
    _patch_players_response(
        context,
        {
            "1": {"first_name": "Joe", "last_name": "Burrow", "position": "QB"},
            "2": {"first_name": "Ja'Marr", "last_name": "Chase", "position": "WR"},
        },
    )


@given("Sleeper returns an empty payload")
def step_empty_payload(context):
    _patch_players_response(context, {})


@when("the player metadata Lambda handler is invoked")
def step_invoke(context):
    ctx = MagicMock(
        aws_request_id="req", function_name="player-metadata-component-test"
    )
    context.pm_error = None
    try:
        context.pm_response = context.player_metadata_handler.lambda_handler({}, ctx)
    except Exception as e:  # noqa: BLE001 - assert on the captured error below
        context.pm_error = e


@then("the handler completes without error")
def step_no_error(context):
    assert context.pm_error is None, f"unexpected error: {context.pm_error!r}"


@then("the handler raises an error")
def step_raises(context):
    assert context.pm_error is not None, "expected the handler to raise, but it did not"


@then("an object exists at the player metadata S3 key")
def step_object_exists(context):
    key = _metadata_key(context)
    assert _object_exists(context, key), f"expected an object at {key}"


@then("no object exists at the player metadata S3 key")
def step_object_absent(context):
    key = _metadata_key(context)
    assert not _object_exists(context, key), f"expected no object at {key}"


@then("the stored payload is a non-empty dict of valid player records")
def step_payload_valid(context):
    obj = context.s3.get_object(Bucket=context.bucket_name, Key=_metadata_key(context))
    players = json.loads(obj["Body"].read())
    assert isinstance(players, dict) and players, (
        f"expected a non-empty dict, got {type(players).__name__}"
    )
    for player in list(players.values())[:10]:
        missing = REQUIRED_PLAYER_FIELDS - set(player.keys())
        assert not missing, f"player record missing {missing}: {player}"
