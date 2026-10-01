"""Steps for the Yahoo lineup backfill (backend/yahoo-lineup-backfill).

The backfill Lambda runs for real against moto S3/DynamoDB/SQS; only Yahoo HTTP and the Yahoo
token engine are mocked. Yahoo's single-team roster responses are synthesized from a fixture of
roster rows, so the round trip (fetch -> lineup store -> manifest self-copy -> processor ->
MATCHUPS lineups) is exercised end to end.
"""

import json
from unittest.mock import MagicMock, patch

from behave import then, when
from common_steps import get_item, load_fixture


class _Response:
    def __init__(self, status, payload=None):
        self.status_code = status
        self._payload = payload or {}

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def _team_roster_payload(team_key, rows):
    """Wrap roster rows in Yahoo's single-team ``roster/players/stats`` JSON shape."""
    players = {
        str(i): {
            "player": [
                [
                    {"player_key": row["player_key"]},
                    {"name": {"full": row["player_name"]}},
                    {"display_position": row["position"]},
                ],
                {"selected_position": [{"position": row["selected_position"]}]},
                {"player_points": {"total": row["points"]}},
            ]
        }
        for i, row in enumerate(rows)
    }
    players["count"] = len(rows)
    return {
        "fantasy_content": {
            "team": [[{"team_key": team_key}], {"roster": {"0": {"players": players}}}]
        }
    }


def _yahoo_responses(context, fixture):
    """Map each team-roster URL to a synthesized Yahoo response."""
    lb = context.lineup_backfill
    by_url = {}
    for record in load_fixture(*fixture.split("/")):
        week = record["data_type"].removeprefix("rosters_week")
        teams: dict[str, list] = {}
        for row in record["data"]["rosters"]:
            teams.setdefault(row["team_key"], []).append(row)
        for team_key, rows in teams.items():
            by_url[lb.team_roster_url(team_key, week)] = _team_roster_payload(
                team_key, rows
            )
    return by_url


def _start_patch(context, patcher):
    patcher.start()
    context._patches.append(patcher)


def _run_backfill(context, get_side_effect):
    lb = context.lineup_backfill
    # The component flow onboards without a caller; the backfill authorizes Yahoo as the owner.
    context.ddb_resource.Table(context.table_name).update_item(
        Key={"PK": f"LEAGUE#{context.canonical}", "SK": "METADATA"},
        UpdateExpression="SET owner_user_id = if_not_exists(owner_user_id, :o)",
        ExpressionAttributeValues={":o": context.default_user},
    )
    context.yahoo_get = MagicMock(side_effect=get_side_effect)
    tokens = MagicMock()
    tokens.return_value.get_valid_access_token.return_value = "tok"
    _start_patch(context, patch.object(lb.requests, "get", context.yahoo_get))
    _start_patch(context, patch.object(lb, "yahoo_tokens_from_env", tokens))
    _start_patch(
        context, patch.dict("os.environ", {"LINEUP_BACKFILL_REQUEST_INTERVAL": "0"})
    )
    # Drain the onboarder's queued message; the step invokes the handler directly.
    context.sqs.purge_queue(QueueUrl=context.backfill_queue_url)
    lambda_context = MagicMock()
    lambda_context.get_remaining_time_in_millis.return_value = 600_000
    event = {
        "Records": [{"body": json.dumps({"canonical_league_id": context.canonical})}]
    }
    context.backfill_result = lb.lambda_handler(event, lambda_context)


@when('the lineup backfill runs with Yahoo rosters from fixture "{fixture}"')
def step_run_backfill(context, fixture):
    responses = _yahoo_responses(context, fixture)
    _run_backfill(context, lambda url, **_: _Response(200, responses[url]))


@when("the lineup backfill runs and Yahoo throttles it")
def step_run_backfill_throttled(context):
    _run_backfill(context, lambda url, **_: _Response(999))


def _delete_league(context):
    """Mirror DELETE /leagues: drop METADATA and every raw S3 object for the league."""
    context.ddb_resource.Table(context.table_name).delete_item(
        Key={"PK": f"LEAGUE#{context.canonical}", "SK": "METADATA"}
    )
    listed = context.s3.list_objects_v2(
        Bucket=context.bucket_name, Prefix=f"raw-api-data/{context.canonical}/"
    )
    for obj in listed.get("Contents", []):
        context.s3.delete_object(Bucket=context.bucket_name, Key=obj["Key"])


@when(
    'the league is deleted while the lineup backfill fetches Yahoo rosters from fixture "{fixture}"'
)
def step_run_backfill_league_deleted(context, fixture):
    responses = _yahoo_responses(context, fixture)
    deleted = []

    def get(url, **_):
        if not deleted:
            _delete_league(context)
            deleted.append(True)
        return _Response(200, responses[url])

    _run_backfill(context, get)


@then("no lineup store exists for the onboarded league")
def step_no_lineup_store(context):
    listed = context.s3.list_objects_v2(
        Bucket=context.bucket_name,
        Prefix=f"raw-api-data/{context.canonical}/yahoo_rosters/",
    )
    assert not listed.get("Contents"), listed


@then('the lineup backfill outcome is "{outcome}"')
def step_backfill_outcome(context, outcome):
    assert context.backfill_result == {"outcomes": [outcome]}, context.backfill_result


@then('the lineup store for season "{season}" has weeks "{weeks}"')
def step_store_weeks(context, season, weeks):
    obj = context.s3.get_object(
        Bucket=context.bucket_name,
        Key=f"raw-api-data/{context.canonical}/yahoo_rosters/{season}.json",
    )
    store = json.loads(obj["Body"].read())
    assert sorted(store["weeks"], key=int) == weeks.split(","), store


@then('the manifest asks the processor to rebuild season "{season}"')
def step_manifest_reprocess(context, season):
    head = context.s3.head_object(
        Bucket=context.bucket_name,
        Key=f"raw-api-data/{context.canonical}/manifest.json",
    )
    assert head["Metadata"].get("reprocess_seasons") == season, head["Metadata"]


@then("the onboarded league has no lineup-pending seasons")
def step_no_pending(context):
    item = get_item(context, f"LEAGUE#{context.canonical}", "METADATA")
    assert not item.get("pending_lineup_seasons"), item


@then('the week {week:d} matchup lists "{player}" as a starter with {points:g} points')
def step_matchup_starter(context, week, player, points):
    rows = context.response.json()["data"]
    starters = [
        s
        for row in rows
        for side in ("team_a_starters", "team_b_starters")
        for s in (row.get(side) or [])
    ]
    match = [s for s in starters if s.get("full_name") == player]
    assert match, f"{player} not among week {week} starters: {starters}"
    assert float(match[0]["points_scored"]) == points, match


@then("a throttled lineup backfill retry is queued for the onboarded league")
def step_retry_queued(context):
    attrs = context.sqs.get_queue_attributes(
        QueueUrl=context.backfill_queue_url,
        AttributeNames=["ApproximateNumberOfMessagesDelayed"],
    )["Attributes"]
    assert attrs["ApproximateNumberOfMessagesDelayed"] == "1", attrs
