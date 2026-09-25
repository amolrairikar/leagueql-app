"""Steps for the FastAPI app as a component (backend/query-precomputed-views..009, backend/app-stats-league-count).

Requests go through the real ``TestClient`` (``context.api``) against moto-backed
DynamoDB/S3; ESPN HTTP is patched where a route reaches out.
"""

import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

from behave import given, then, when
from boto3.dynamodb.conditions import Key
from common_steps import get_item, put_item


def _seed_matchup_week(context, canonical, season, week, *, played):
    # A played week stores real scores; an unplayed week (ESPN pre-stores the whole
    # season schedule) stores a 0-0 row. The refresh up-to-date guard must judge
    # "current" against the latest *played* week only (backend/league-refresh).
    score = Decimal("118.0") if played else Decimal(0)
    put_item(
        context,
        {
            "PK": f"LEAGUE#{canonical}",
            "SK": f"MATCHUPS#{season}#WEEK#{int(week):02d}",
            "data": [{"team_a_score": score, "team_b_score": score}],
        },
    )


def _iso(days):
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


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


@given('league "{canonical}" has team rows for seasons "{seasons}"')
def step_seed_teams(context, canonical, seasons):
    # TEAMS is stored once across all seasons; each row carries its own season so the
    # export can filter it per requested season (backend/league-export).
    rows = [
        {"team_id": str(i + 1), "season": season}
        for i, season in enumerate(s.strip() for s in seasons.split(","))
    ]
    put_item(
        context,
        {"PK": f"LEAGUE#{canonical}", "SK": "TEAMS", "data": rows},
    )


@then('the export response has season "{season}"')
def step_export_has_season(context, season):
    data = context.response.json()["data"]
    assert season in data, context.response.text


@then('the export season "{season}" has view "{view}" with {count:d} row(s)')
def step_export_view_rows(context, season, view, count):
    data = context.response.json()["data"]
    assert season in data, context.response.text
    assert view in data[season], f"{view} missing in {season}: {context.response.text}"
    actual = len(data[season][view])
    assert actual == count, f"expected {count} {view} rows, got {actual}"


@then('the export season "{season}" has no view "{view}"')
def step_export_no_view(context, season, view):
    data = context.response.json()["data"]
    assert view not in data.get(season, {}), context.response.text


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


def _yahoo_leagues_payload(league_id, league_key):
    return {
        "fantasy_content": {
            "users": {
                "0": {
                    "user": [
                        {},
                        {
                            "games": {
                                "0": {
                                    "game": [
                                        {"game_key": "461", "game_code": "nfl"},
                                        {
                                            "leagues": {
                                                "0": {
                                                    "league": [
                                                        {
                                                            "league_key": league_key,
                                                            "league_id": league_id,
                                                            "season": "2025",
                                                        }
                                                    ]
                                                },
                                                "count": 1,
                                            }
                                        },
                                    ]
                                },
                                "count": 1,
                            }
                        },
                    ]
                },
                "count": 1,
            }
        }
    }


def _yahoo_teams_payload():
    return {
        "fantasy_content": {
            "league": [
                {},
                {
                    "teams": {
                        "0": {
                            "team": [
                                [
                                    {"team_key": "461.l.456.t.1"},
                                    # Yahoo returns a team's nested managers as a plain list.
                                    {
                                        "managers": [
                                            {
                                                "manager": {
                                                    "manager_id": "1",
                                                    "guid": "G1",
                                                    "nickname": "Alice",
                                                }
                                            }
                                        ]
                                    },
                                ]
                            ]
                        },
                        "count": 1,
                    }
                },
            ]
        }
    }


def _patch_yahoo_token(context, *, linked):
    """Patch the API's Yahoo token resolution; unlinked raises YahooReauthRequired -> 403."""
    import routes

    from common.yahoo_tokens import YahooReauthRequired

    token = (
        MagicMock(return_value="access-tok")
        if linked
        else MagicMock(side_effect=YahooReauthRequired("no link"))
    )
    patcher = patch.object(routes.yahoo_oauth, "get_valid_access_token", token)
    patcher.start()
    context._patches.append(patcher)


def _patch_yahoo_http(context, *, seeded_league_id):
    """Patch the upstream Yahoo GETs: leagues enumeration then that league's teams."""
    import routes

    leagues_resp = MagicMock()
    leagues_resp.raise_for_status.return_value = None
    leagues_resp.json.return_value = _yahoo_leagues_payload(
        seeded_league_id, f"461.l.{seeded_league_id}"
    )
    teams_resp = MagicMock()
    teams_resp.raise_for_status.return_value = None
    teams_resp.json.return_value = _yahoo_teams_payload()
    patcher = patch.object(
        routes.http_requests, "get", MagicMock(side_effect=[leagues_resp, teams_resp])
    )
    patcher.start()
    context._patches.append(patcher)


@when(
    'I POST to yahoo_members for league "{league_id}" targeting Yahoo league '
    '"{yahoo_league_id}" with a linked account'
)
def step_post_yahoo_members_linked(context, league_id, yahoo_league_id):
    _patch_yahoo_token(context, linked=True)
    _patch_yahoo_http(context, seeded_league_id=yahoo_league_id)
    context.response = context.api.post(
        f"/leagues/{league_id}/yahoo_members"
        f"?platform=SLEEPER&yahooLeagueId={yahoo_league_id}"
    )


@when(
    'I POST to yahoo_members for league "{league_id}" targeting Yahoo league '
    '"{yahoo_league_id}" without a link'
)
def step_post_yahoo_members_unlinked(context, league_id, yahoo_league_id):
    _patch_yahoo_token(context, linked=False)
    context.response = context.api.post(
        f"/leagues/{league_id}/yahoo_members"
        f"?platform=SLEEPER&yahooLeagueId={yahoo_league_id}"
    )


@when(
    'I POST to yahoo_members for league "{league_id}" targeting Yahoo league '
    '"{yahoo_league_id}" not in the account'
)
def step_post_yahoo_members_not_in_account(context, league_id, yahoo_league_id):
    _patch_yahoo_token(context, linked=True)
    # The enumerated leagues contain a different id, so resolution misses -> 404.
    _patch_yahoo_http(context, seeded_league_id="111")
    context.response = context.api.post(
        f"/leagues/{league_id}/yahoo_members"
        f"?platform=SLEEPER&yahooLeagueId={yahoo_league_id}"
    )


@when(
    'I POST a Yahoo migration of league "{league_id}" from "{platform}" to '
    'league "{new_league_id}" with a linked account'
)
def step_post_yahoo_migration_linked(context, league_id, platform, new_league_id):
    import routes

    patcher = patch.object(
        routes.yahoo_oauth, "has_valid_link", MagicMock(return_value=True)
    )
    patcher.start()
    context._patches.append(patcher)
    context.response = context.api.post(
        f"/leagues/{league_id}/migrate?platform={platform}",
        json={
            "newPlatformLeagueId": new_league_id,
            "newPlatform": "YAHOO",
            "managerMapping": [
                {
                    "currentPlatformOwnerId": "u1",
                    "newPlatformOwnerId": "G1",
                    "displayName": "Alice",
                }
            ],
        },
    )


@when(
    'I POST a Yahoo migration of league "{league_id}" from "{platform}" to '
    'league "{new_league_id}" without a link'
)
def step_post_yahoo_migration_unlinked(context, league_id, platform, new_league_id):
    import routes

    patcher = patch.object(
        routes.yahoo_oauth, "has_valid_link", MagicMock(return_value=False)
    )
    patcher.start()
    context._patches.append(patcher)
    context.response = context.api.post(
        f"/leagues/{league_id}/migrate?platform={platform}",
        json={
            "newPlatformLeagueId": new_league_id,
            "newPlatform": "YAHOO",
            "managerMapping": [
                {
                    "currentPlatformOwnerId": "u1",
                    "newPlatformOwnerId": "G1",
                    "displayName": "Alice",
                }
            ],
        },
    )


@when('I POST a REFRESH of league "{league_id}" on "{platform}"')
def step_post_refresh(context, league_id, platform):
    # requestType is a query param; the REFRESH path of an already-onboarded
    # league is owner-gated (backend/league-authorization).
    context.response = context.api.post(
        "/leagues?requestType=REFRESH",
        json={"leagueId": league_id, "platform": platform},
    )


@given('the current NFL state is season "{season}" week "{week}"')
def step_patch_api_nfl_state(context, season, week):
    # Patch the API's NFL-state fetch (routes imports get_nfl_state by name) so the
    # refresh up-to-date guard runs against a known season/week without real HTTP.
    import routes

    state = {"season_type": "regular", "season": season, "week": week}
    patcher = patch.object(routes, "get_nfl_state", MagicMock(return_value=state))
    patcher.start()
    context._patches.append(patcher)


@given('league "{canonical}" has a played matchup for season "{season}" week "{week}"')
def step_seed_played_matchup(context, canonical, season, week):
    _seed_matchup_week(context, canonical, season, week, played=True)


@given(
    'league "{canonical}" has an unplayed matchup for season "{season}" week "{week}"'
)
def step_seed_unplayed_matchup(context, canonical, season, week):
    _seed_matchup_week(context, canonical, season, week, played=False)


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


@then('no LEAGUE_LOOKUP record exists for league "{league_id}" platform "{platform}"')
def step_lookup_not_written(context, league_id, platform):
    item = get_item(context, f"LEAGUE#{league_id}#PLATFORM#{platform}", "LEAGUE_LOOKUP")
    assert not item, "unexpected LEAGUE_LOOKUP written by the API"


@then("the onboarder Lambda was invoked")
def step_onboarder_invoked(context):
    assert context.main.lambda_client.invoke.called, "onboarder Lambda not invoked"


@then("the query response has {count:d} row(s)")
def step_query_rows(context, count):
    data = context.response.json()["data"]
    assert len(data) == count, f"expected {count} rows, got {len(data)}: {data}"


@then('no query response row has "{field}" equal to "{value}"')
def step_no_row_field_equals(context, field, value):
    data = context.response.json()["data"]
    offenders = [row for row in data if str(row.get(field)) == value]
    assert not offenders, f"rows with {field}={value}: {offenders}"


@then('a query response row has "{field}" equal to "{value}"')
def step_row_field_equals(context, field, value):
    data = context.response.json()["data"]

    def matches(actual):
        if isinstance(actual, (int, float)):
            try:
                return float(actual) == float(value)
            except ValueError:
                return False
        return str(actual) == value

    found = [row for row in data if matches(row.get(field))]
    assert found, f"no row with {field}={value} in {data}"


@then('the response data field "{field}" equals "{value}"')
def step_data_field(context, field, value):
    actual = context.response.json()["data"].get(field)
    assert str(actual) == value, f"{field}={actual!r}"


@then('the response data field "{field}" is null')
def step_data_field_null(context, field):
    assert context.response.json()["data"].get(field) is None


@then('the response data field "{field}" is present')
def step_data_field_present(context, field):
    assert context.response.json()["data"].get(field) is not None, (
        f"{field} was missing/null"
    )


@then('the job status is "{status}"')
def step_job_status_api(context, status):
    assert context.response.json()["data"]["status"] == status, context.response.text


@then('the response has Cache-Control "{value}"')
def step_cache_control(context, value):
    assert context.response.headers.get("cache-control") == value, dict(
        context.response.headers
    )


@then("the response carries the standard security headers")
def step_security_headers(context):
    expected = {
        "x-content-type-options": "nosniff",
        "content-security-policy": (
            "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
        ),
        "strict-transport-security": "max-age=63072000; includeSubDomains",
        "x-frame-options": "DENY",
    }
    headers = context.response.headers
    for header, value in expected.items():
        assert headers.get(header) == value, dict(headers)


@then('no DynamoDB items remain for league "{canonical}"')
def step_no_items(context, canonical):
    table = context.ddb_resource.Table(context.table_name)
    resp = table.query(KeyConditionExpression=Key("PK").eq(f"LEAGUE#{canonical}"))
    assert not resp["Items"], f"items remain: {resp['Items']}"


@then('a METADATA item still exists for league "{canonical}"')
def step_metadata_survives(context, canonical):
    assert get_item(context, f"LEAGUE#{canonical}", "METADATA"), "METADATA was deleted"


@given('league "{canonical}" was last refreshed {days:d} days ago')
def step_seed_last_refresh(context, canonical, days):
    # Seed last_refresh_at so the weekly refresh cooldown can be exercised
    # (backend/league-refresh). Written by the processor on a successful refresh;
    # here we set it directly to drive the API cooldown check.
    seeded = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    context.ddb_resource.Table(context.table_name).update_item(
        Key={"PK": f"LEAGUE#{canonical}", "SK": "METADATA"},
        UpdateExpression="SET last_refresh_at = :t",
        ExpressionAttributeValues={":t": seeded},
    )


@given('league "{canonical}" was last accessed {minutes:d} minutes ago')
def step_seed_last_accessed(context, canonical, minutes):
    # Seed a recent last_accessed_at and stash it so a later assertion can confirm
    # the throttle held (no overwrite within the window). backend/league-access-tracking.
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


@given("an ESPN_CREDENTIALS item exists for the default user")
def step_seed_espn_credentials(context):
    # The delete/opt-out cleanup only reads/removes the item, so no real KMS ciphertext
    # is needed (backend/espn-credential-storage).
    put_item(
        context,
        {
            "PK": f"USER#{context.default_user}",
            "SK": "ESPN_CREDENTIALS",
            "swid": "ciphertext-swid",
            "espn_s2": "ciphertext-s2",
            "updated_at": 1,
        },
    )


@given(
    'an onboarded ESPN league "{canonical}" opted into auto-refresh owned by the default user'
)
def step_seed_optedin_espn_league(context, canonical):
    # A full METADATA item (with onboarded_at so it projects into GSI3) opted into
    # auto-refresh, so the owner still has another opted-in ESPN league.
    put_item(
        context,
        {
            "PK": f"LEAGUE#{canonical}",
            "SK": "METADATA",
            "platform": "ESPN",
            "league_name": "Other ESPN League",
            "owner_user_id": context.default_user,
            "onboarded_at": "2024-09-01T00:00:00Z",
            "auto_refresh_enabled": True,
        },
    )


@then("no ESPN_CREDENTIALS item exists for the default user")
def step_assert_espn_credentials_absent(context):
    item = get_item(context, f"USER#{context.default_user}", "ESPN_CREDENTIALS")
    assert item is None, "expected the ESPN_CREDENTIALS item to be deleted"


@then("an ESPN_CREDENTIALS item still exists for the default user")
def step_assert_espn_credentials_present(context):
    item = get_item(context, f"USER#{context.default_user}", "ESPN_CREDENTIALS")
    assert item is not None, "expected the ESPN_CREDENTIALS item to be retained"


@when('I PUT auto-refresh "{enabled}" for "{path}"')
def step_put_auto_refresh(context, enabled, path):
    context.response = context.api.put(path, json={"enabled": enabled == "true"})


@then('the METADATA auto_refresh_enabled for league "{canonical}" is "{value}"')
def step_assert_metadata_auto_refresh(context, canonical, value):
    item = get_item(context, f"LEAGUE#{canonical}", "METADATA")
    assert item is not None, "expected a METADATA item"
    expected = value == "true"
    assert bool(item.get("auto_refresh_enabled")) == expected, item
