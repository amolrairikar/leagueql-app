"""Steps for the FastAPI app as a component (BE-005..009, BE-013).

Requests go through the real ``TestClient`` (``context.api``) against moto-backed
DynamoDB/S3; ESPN HTTP is patched where a route reaches out.
"""

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from behave import given, then, when
from boto3.dynamodb.conditions import Key
from common_steps import get_item, put_item


def _iso(days):
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


@given("the LEAGUE_COUNT starts at {count:d}")
def step_seed_count(context, count):
    put_item(
        context,
        {"PK": "APP#STATS", "SK": "LEAGUE_COUNT", "league_count": count},
    )


@given('league "{canonical}" has a "{sk}" view with {count:d} row(s)')
def step_seed_view(context, canonical, sk, count):
    put_item(
        context,
        {
            "PK": f"LEAGUE#{canonical}",
            "SK": sk,
            "data": [{"week": i + 1, "score": 100 + i} for i in range(count)],
        },
    )


@given('a JOB_STATUS "{status}" exists for job "{job_id}"')
def step_seed_job(context, status, job_id):
    item = {
        "PK": f"JOB#{job_id}",
        "SK": "JOB_STATUS",
        "status": status,
        "request_type": "ONBOARD",
    }
    if status == "FAILED":
        item["failure_code"] = "UPSTREAM"
        item["failure_reason"] = "We couldn't reach the platform right now."
    put_item(context, item)


@given('league "{canonical}" has raw data stored in S3')
def step_seed_s3_raw(context, canonical):
    context.s3.put_object(
        Bucket=context.bucket_name,
        Key=f"raw-api-data/{canonical}/manifest.json",
        Body=json.dumps({"SLEEPER": ["2024"]}),
    )
    context.s3.put_object(
        Bucket=context.bucket_name,
        Key=f"raw-api-data/{canonical}/2024.json",
        Body=json.dumps([]),
    )


@when('I POST to espn_members for league "{league_id}" with ESPN returning {code:d}')
def step_post_espn_members(context, league_id, code):
    import routes

    resp = MagicMock(status_code=code)
    if code == 200:
        resp.json.return_value = {
            "members": [
                {"id": "m1", "displayName": "Manager One"},
                {"id": "m2"},
            ]
        }
        resp.raise_for_status.return_value = None
    else:
        import requests

        err = requests.exceptions.HTTPError("boom")
        resp.raise_for_status.side_effect = err
    patcher = patch.object(routes.http_requests, "get", MagicMock(return_value=resp))
    patcher.start()
    context._patches.append(patcher)
    context.response = context.api.post(
        f"/leagues/{league_id}/espn_members"
        "?platform=SLEEPER&espnLeagueId=999&season=2024",
        json={"swid": "{SWID}", "s2": "s2cookie"},
    )


@when('I POST a REFRESH of league "{league_id}" on "{platform}"')
def step_post_refresh(context, league_id, platform):
    # requestType is a query param; the REFRESH path of an already-onboarded
    # league is owner-gated (LQL-01 / BE-016).
    context.response = context.api.post(
        "/leagues?requestType=REFRESH",
        json={"leagueId": league_id, "platform": platform},
    )


@when(
    'I POST a migration of league "{league_id}" from "{platform}" to '
    '"{new_platform}" league "{new_league_id}"'
)
def step_post_migration(context, league_id, platform, new_platform, new_league_id):
    context.response = context.api.post(
        f"/leagues/{league_id}/migrate?platform={platform}",
        json={
            "newPlatformLeagueId": new_league_id,
            "newPlatform": new_platform,
            "season": "2024",
            "managerMapping": [
                {
                    "currentPlatformOwnerId": "u1",
                    "newPlatformOwnerId": "u2",
                    "displayName": "Manager One",
                }
            ],
        },
    )


@when(
    'I POST a migration of league "{league_id}" from "{platform}" to '
    '"{new_platform}" league "{new_league_id}" with an unknown mapping key'
)
def step_post_migration_bad_mapping(
    context, league_id, platform, new_platform, new_league_id
):
    context.response = context.api.post(
        f"/leagues/{league_id}/migrate?platform={platform}",
        json={
            "newPlatformLeagueId": new_league_id,
            "newPlatform": new_platform,
            "season": "2024",
            "managerMapping": [
                {
                    "currentPlatformOwnerId": "u1",
                    "newPlatformOwnerId": "u2",
                    "displayName": "Manager One",
                    "extraField": "nope",
                }
            ],
        },
    )


@then('a PLATFORM_MIGRATION item exists for league "{canonical}"')
def step_migration_item(context, canonical):
    table = context.ddb_resource.Table(context.table_name)
    resp = table.query(
        KeyConditionExpression=Key("PK").eq(f"LEAGUE#{canonical}")
        & Key("SK").begins_with("PLATFORM_MIGRATION#")
    )
    assert resp["Items"], "no PLATFORM_MIGRATION item written"


@then('no PLATFORM_MIGRATION item exists for league "{canonical}"')
def step_no_migration_item(context, canonical):
    table = context.ddb_resource.Table(context.table_name)
    resp = table.query(
        KeyConditionExpression=Key("PK").eq(f"LEAGUE#{canonical}")
        & Key("SK").begins_with("PLATFORM_MIGRATION#")
    )
    assert not resp["Items"], "unexpected PLATFORM_MIGRATION item written"


@then(
    'a LEAGUE_LOOKUP record was written for league "{league_id}" platform '
    '"{platform}" with canonical "{canonical}"'
)
def step_lookup_written(context, league_id, platform, canonical):
    item = get_item(context, f"LEAGUE#{league_id}#PLATFORM#{platform}", "LEAGUE_LOOKUP")
    assert item, "LEAGUE_LOOKUP not written"
    assert item.get("canonical_league_id") == canonical, item


@then("the onboarder Lambda was invoked")
def step_onboarder_invoked(context):
    assert context.main.lambda_client.invoke.called, "onboarder Lambda not invoked"


@then("the query response has {count:d} row(s)")
def step_query_rows(context, count):
    data = context.response.json()["data"]
    assert len(data) == count, f"expected {count} rows, got {len(data)}: {data}"


@then('the response data field "{field}" equals "{value}"')
def step_data_field(context, field, value):
    actual = context.response.json()["data"].get(field)
    assert str(actual) == value, f"{field}={actual!r}"


@then('the response data field "{field}" is null')
def step_data_field_null(context, field):
    assert context.response.json()["data"].get(field) is None


@then('the job status is "{status}"')
def step_job_status_api(context, status):
    assert context.response.json()["data"]["status"] == status, context.response.text


@then('the response has Cache-Control "{value}"')
def step_cache_control(context, value):
    assert context.response.headers.get("cache-control") == value, dict(
        context.response.headers
    )


@then('no DynamoDB items remain for league "{canonical}"')
def step_no_items(context, canonical):
    table = context.ddb_resource.Table(context.table_name)
    resp = table.query(KeyConditionExpression=Key("PK").eq(f"LEAGUE#{canonical}"))
    assert not resp["Items"], f"items remain: {resp['Items']}"


@then('a METADATA item still exists for league "{canonical}"')
def step_metadata_survives(context, canonical):
    assert get_item(context, f"LEAGUE#{canonical}", "METADATA"), "METADATA was deleted"


@given('league "{canonical}" was last accessed {minutes:d} minutes ago')
def step_seed_last_accessed(context, canonical, minutes):
    # Seed a recent last_accessed_at and stash it so a later assertion can confirm
    # the throttle held (no overwrite within the window). BE-018.
    seeded = (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()
    context.ddb_resource.Table(context.table_name).update_item(
        Key={"PK": f"LEAGUE#{canonical}", "SK": "METADATA"},
        UpdateExpression="SET last_accessed_at = :t",
        ExpressionAttributeValues={":t": seeded},
    )
    context.seeded_last_accessed = seeded


@then('league "{canonical}" has a last_accessed_at timestamp')
def step_last_accessed_present(context, canonical):
    item = get_item(context, f"LEAGUE#{canonical}", "METADATA")
    assert item and item.get("last_accessed_at"), "last_accessed_at was not recorded"


@then('league "{canonical}" last_accessed_at is unchanged')
def step_last_accessed_unchanged(context, canonical):
    item = get_item(context, f"LEAGUE#{canonical}", "METADATA")
    assert item.get("last_accessed_at") == context.seeded_last_accessed, (
        "last_accessed_at was overwritten within the throttle window"
    )
