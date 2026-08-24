"""Steps driving the onboarder -> processor component chain (BE-001, BE-004).

The external platform API is mocked by replacing ``OnboardingService._build_client``
with a fake client that returns fixture raw data; everything downstream — the
DynamoDB/S3 writes, the synthesized S3 trigger, the processor, and the DuckDB
transforms — runs for real against the moto-backed stack.
"""

import json
import uuid
from unittest.mock import MagicMock, patch

from behave import given, then, when
from common_steps import get_item, load_fixture


class _FakeClient:
    """Stand-in for ESPNClient/SleeperClient returning canned fixture data."""

    def __init__(self, raw_data, pending_season=None):
        self._raw = raw_data
        self._seasons = sorted({str(item["season"]) for item in raw_data})
        self._pending_season = pending_season

    def get_seasons(self):
        return self._seasons

    def get_pending_season(self):
        return self._pending_season

    async def fetch_all(self):
        return self._raw


def _patch_build_client(context, raw_data, pending_season=None):
    patcher = patch.object(
        context.onboarding_service_mod.OnboardingService,
        "_build_client",
        lambda self, **kwargs: _FakeClient(raw_data, pending_season=pending_season),
    )
    patcher.start()
    context._patches.append(patcher)


def _run_onboarder(
    context, platform, league_id, request_type="ONBOARD", body_extra=None
):
    context.correlation_id = str(uuid.uuid4())
    body = {"leagueId": league_id, "platform": platform}
    if body_extra:
        body.update(body_extra)
    event = {
        "requestType": request_type,
        "correlation_id": context.correlation_id,
        "body": body,
    }
    if getattr(context, "canonical", None):
        event["canonicalLeagueId"] = context.canonical
    # The handler walks the Sleeper previous_league_id chain (a real HTTP call) for any
    # ONBOARD/REFRESH without a known canonical. Stub it so resolution is driven by the
    # scenario (``context.resolved_canonical``, default None = a brand-new league) instead
    # of hitting the network; the real chain walk is covered by unit tests.
    resolve_patch = patch.object(
        context.onboarder_handler,
        "resolve_sleeper_canonical_league_id",
        return_value=getattr(context, "resolved_canonical", None),
    )
    resolve_patch.start()
    context._patches.append(resolve_patch)
    ctx = MagicMock(aws_request_id="req", function_name="onboarder-test")
    context.onboard_response = context.onboarder_handler.lambda_handler(event, ctx)
    parsed = json.loads(context.onboard_response["body"])
    if parsed.get("canonical_league_id"):
        context.canonical = parsed["canonical_league_id"]


@given("Sleeper player metadata and stats are cached in S3")
def step_seed_player_cache(context):
    context.s3.put_object(
        Bucket=context.bucket_name,
        Key="player-metadata/sleeper_nfl_players.json",
        Body=json.dumps(load_fixture("sleeper", "player_metadata.json")),
    )
    context.s3.put_object(
        Bucket=context.bucket_name,
        Key="player-stats/sleeper_nfl_player_stats.json",
        Body=json.dumps(load_fixture("sleeper", "player_stats.json")),
    )


@given("Sleeper player metadata is cached in S3 with no player stats")
def step_seed_player_cache_no_stats(context):
    # A Sleeper league onboarded before its first games (e.g. a new season created in the
    # preseason) has player metadata but no accumulated stats yet, so the stats object is
    # empty. player_scoring_totals then computes to no rows — the empty-view guard must let
    # the processor build the remaining views (DRAFT included) instead of crashing.
    context.s3.put_object(
        Bucket=context.bucket_name,
        Key="player-metadata/sleeper_nfl_players.json",
        Body=json.dumps(load_fixture("sleeper", "player_metadata.json")),
    )
    context.s3.put_object(
        Bucket=context.bucket_name,
        Key="player-stats/sleeper_nfl_player_stats.json",
        Body=json.dumps({}),
    )


@when(
    'the onboarder runs an ONBOARD for "{platform}" league "{league_id}" '
    'with fixture "{fixture}"'
)
def step_onboard(context, platform, league_id, fixture):
    raw_data = load_fixture(*fixture.split("/"))
    _patch_build_client(context, raw_data)
    _run_onboarder(context, platform, league_id, "ONBOARD")


@when(
    'the onboarder runs a REFRESH for "{platform}" league "{league_id}" '
    'with fixture "{fixture}"'
)
def step_refresh(context, platform, league_id, fixture):
    raw_data = load_fixture(*fixture.split("/"))
    _patch_build_client(context, raw_data)
    _run_onboarder(context, platform, league_id, "REFRESH")


@when("the onboarder fails to reach the platform")
def step_onboard_http_error(context):
    import requests

    def _boom(self, **kwargs):
        client = MagicMock()
        client.get_seasons.return_value = ["2024"]
        resp = MagicMock(status_code=401)
        error = requests.exceptions.HTTPError("401 Unauthorized")
        error.response = resp

        async def _fetch_all():
            raise error

        client.fetch_all.side_effect = _fetch_all
        return client

    patcher = patch.object(
        context.onboarding_service_mod.OnboardingService, "_build_client", _boom
    )
    patcher.start()
    context._patches.append(patcher)
    _run_onboarder(context, "ESPN", "555", "ONBOARD", {"season": "2024"})


@when(
    'the onboarder runs an ONBOARD for "{platform}" league "{league_id}" '
    'with no started seasons pending "{pending}"'
)
def step_onboard_pending(context, platform, league_id, pending):
    # An offseason renewal: no usable seasons yet, but the not-yet-started season is
    # reported as pending so the new league ID can be registered for later pickup.
    _patch_build_client(context, [], pending_season=pending)
    _run_onboarder(context, platform, league_id, "ONBOARD")


@given('the Sleeper previous_league_id chain resolves to canonical "{canonical}"')
def step_chain_resolves(context, canonical):
    # Drives the stubbed resolve_sleeper_canonical_league_id in _run_onboarder so a
    # renewed Sleeper season (new league ID) maps back to an already-onboarded league.
    context.resolved_canonical = canonical


@then(
    'a pending LEAGUE_LOOKUP exists for league "{league_id}" '
    'pending season "{season}" canonical "{canonical}"'
)
def step_pending_lookup(context, league_id, season, canonical):
    item = get_item(context, f"LEAGUE#{league_id}#PLATFORM#SLEEPER", "LEAGUE_LOOKUP")
    assert item, "no pending LEAGUE_LOOKUP written"
    assert item["canonical_league_id"] == canonical
    assert item.get("pending_season") == season
    # No seasons set yet — the not-yet-started season must not surface until it has data.
    assert "seasons" not in item


@then('exactly one un-overwritten METADATA exists for canonical "{canonical}"')
def step_single_metadata_preserved(context, canonical):
    from boto3.dynamodb.conditions import Key

    table = context.ddb_resource.Table(context.table_name)
    resp = table.query(
        KeyConditionExpression=Key("PK").eq(f"LEAGUE#{canonical}")
        & Key("SK").eq("METADATA")
    )
    items = resp["Items"]
    assert len(items) == 1, f"expected exactly one METADATA, got {len(items)}"
    # A duplicate/overwrite from the ONBOARD write path would replace the seeded
    # METADATA with one that drops the original owner (no ownerUserId on this event),
    # so a surviving owner_user_id proves the original record was preserved.
    assert items[0].get("owner_user_id"), "METADATA was overwritten by onboarding"


@when("the processor processes the onboarded league")
def step_process(context):
    manifest_key = f"raw-api-data/{context.canonical}/manifest.json"
    s3_event = {
        "Records": [
            {
                "userIdentity": {"principalId": "AROAEXAMPLE:tester"},
                "s3": {
                    "bucket": {"name": context.bucket_name},
                    "object": {"key": manifest_key},
                },
            }
        ]
    }
    context.processor_handler.lambda_handler(s3_event, None)


@then("the onboarder returns status {code:d}")
def step_onboard_status(context, code):
    assert context.onboard_response["statusCode"] == code, context.onboard_response


@then('a JOB_STATUS "{status}" exists for the job')
def step_job_status(context, status):
    item = get_item(context, f"JOB#{context.correlation_id}", "JOB_STATUS")
    assert item, "no JOB_STATUS item written"
    assert item["status"] == status, f"job status was {item['status']}"


@then('the JOB_STATUS failure_code is "{code}"')
def step_job_failure_code(context, code):
    item = get_item(context, f"JOB#{context.correlation_id}", "JOB_STATUS")
    assert item and item.get("failure_code") == code, item


@then("a METADATA item exists for the onboarded league")
def step_metadata_exists(context):
    assert get_item(context, f"LEAGUE#{context.canonical}", "METADATA"), "no METADATA"


@then("no METADATA item exists for the onboarded league")
def step_no_metadata(context):
    if getattr(context, "canonical", None):
        assert not get_item(context, f"LEAGUE#{context.canonical}", "METADATA")


@then('a LEAGUE_LOOKUP exists for onboarded league "{league_id}" platform "{platform}"')
def step_lookup_exists(context, league_id, platform):
    item = get_item(context, f"LEAGUE#{league_id}#PLATFORM#{platform}", "LEAGUE_LOOKUP")
    assert item, "no LEAGUE_LOOKUP"
    assert item["canonical_league_id"] == context.canonical


@then('the league has at least one "{sk_prefix}" item')
def step_has_entity(context, sk_prefix):
    from boto3.dynamodb.conditions import Key

    table = context.ddb_resource.Table(context.table_name)
    resp = table.query(
        KeyConditionExpression=Key("PK").eq(f"LEAGUE#{context.canonical}")
        & Key("SK").begins_with(sk_prefix)
    )
    assert resp["Items"], f"no {sk_prefix} items found"
    context.last_items = resp["Items"]


@then('the league has exactly {count:d} "{sk_prefix}" item(s)')
def step_exact_count(context, count, sk_prefix):
    from boto3.dynamodb.conditions import Key

    table = context.ddb_resource.Table(context.table_name)
    resp = table.query(
        KeyConditionExpression=Key("PK").eq(f"LEAGUE#{context.canonical}")
        & Key("SK").begins_with(sk_prefix)
    )
    assert len(resp["Items"]) == count, (
        f"expected {count} {sk_prefix} items, got {len(resp['Items'])}"
    )


@then("the LEAGUE_COUNT is {count:d}")
def step_league_count(context, count):
    item = get_item(context, "APP#STATS", "LEAGUE_COUNT")
    actual = int(item["league_count"]) if item else 0
    assert actual == count, f"LEAGUE_COUNT was {actual}"


@then('the standings show "{team_name}" as champion')
def step_champion(context, team_name):
    item = get_item(context, f"LEAGUE#{context.canonical}", "STANDINGS#2024")
    champs = [row["team_name"] for row in item["data"] if row.get("champion") == "Yes"]
    assert team_name in champs, f"champions were {champs}"
