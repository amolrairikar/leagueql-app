"""Steps for the nightly unused-league reaper Lambda (backend/league-reaper)."""

import os
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

from behave import given, then, when
from boto3.dynamodb.conditions import Attr
from common_steps import get_item, put_item


def _days_ago(days: int) -> str:
    return (datetime.now(UTC) - timedelta(days=days)).isoformat()


def _seed_raw_data(context, canonical):
    context.s3.put_object(
        Bucket=context.bucket_name,
        Key=f"raw-api-data/{canonical}/2024.json",
        Body=b"[]",
    )


def _raw_keys(context, canonical) -> list[str]:
    response = context.s3.list_objects_v2(
        Bucket=context.bucket_name, Prefix=f"raw-api-data/{canonical}/"
    )
    return [obj["Key"] for obj in response.get("Contents", [])]


def _league_items(context, canonical) -> list[dict]:
    """Every item in the league's partition plus its LEAGUE_LOOKUP entries."""
    items = context.ddb_resource.Table(context.table_name).scan(
        FilterExpression=Attr("PK").eq(f"LEAGUE#{canonical}")
        | Attr("canonical_league_id").eq(canonical)
    )
    return items["Items"]


def _seed_league(context, canonical, platform, **metadata):
    put_item(
        context,
        {
            "PK": f"LEAGUE#{canonical}",
            "SK": "METADATA",
            "platform": platform,
            "league_name": f"League {canonical}",
            "owner_user_id": context.default_user,
            **metadata,
        },
    )
    put_item(
        context,
        {
            "PK": f"LEAGUE#id-{canonical}#PLATFORM#{platform}",
            "SK": "LEAGUE_LOOKUP",
            "canonical_league_id": canonical,
            "platform": platform,
            "league_id": f"id-{canonical}",
        },
    )
    put_item(context, {"PK": f"LEAGUE#{canonical}", "SK": "STANDINGS#2024"})
    put_item(
        context,
        {
            "PK": f"LEAGUE#{canonical}",
            "SK": f"MEMBER#{context.default_user}",
            "member_user_id": context.default_user,
            "joined_at": metadata["onboarded_at"],
        },
    )
    _seed_raw_data(context, canonical)


@given(
    'an idle "{platform}" league "{canonical}" with views, a lookup, a member, '
    "and raw data"
)
def step_seed_idle(context, platform, canonical):
    _seed_league(
        context,
        canonical,
        platform,
        onboarded_at=_days_ago(800),
        last_accessed_at=_days_ago(400),
    )


@given('an active league "{canonical}" that was onboarded long ago but opened recently')
def step_seed_active_league(context, canonical):
    _seed_league(
        context,
        canonical,
        "SLEEPER",
        onboarded_at=_days_ago(800),
        last_accessed_at=_days_ago(1),
    )


@given('the idle league "{canonical}" has a job in progress')
def step_seed_job(context, canonical):
    context.ddb_resource.Table(context.table_name).update_item(
        Key={"PK": f"LEAGUE#{canonical}", "SK": "METADATA"},
        UpdateExpression="SET active_job_id = :j",
        ExpressionAttributeValues={":j": "job-1"},
    )
    put_item(context, {"PK": "JOB#job-1", "SK": "JOB_STATUS", "status": "IN_PROGRESS"})


def _run_reaper(context, dry_run: str):
    handler = context.league_reaper_handler
    post = MagicMock()
    for patcher in (
        patch.object(handler._session, "post", post),
        patch.dict(os.environ, {"LEAGUE_REAPER_DRY_RUN": dry_run}),
    ):
        patcher.start()
        context._patches.append(patcher)

    lambda_context = MagicMock()
    lambda_context.get_remaining_time_in_millis.return_value = 900_000
    handler.lambda_handler({}, lambda_context)
    context.reaper_embed = post.call_args.kwargs["json"]["embeds"][0]


@when("the league reaper runs with deletion enabled")
def step_run_live(context):
    _run_reaper(context, "false")


@when("the league reaper runs as a dry run")
def step_run_dry(context):
    _run_reaper(context, "true")


@then('nothing remains of league "{canonical}"')
def step_nothing_remains(context, canonical):
    items = _league_items(context, canonical)
    assert not items, f"items remain: {items}"
    assert not _raw_keys(context, canonical), "raw S3 data remains"


@then('league "{canonical}" still has raw data in S3')
def step_raw_data_kept(context, canonical):
    assert _raw_keys(context, canonical), "raw S3 data was deleted"


@then("a YAHOO_OAUTH token item exists for the default user afterwards")
def step_token_kept(context):
    assert get_item(context, f"USER#{context.default_user}", "YAHOO_OAUTH")


@then('the reaper summary reports {count:d} under "{name}"')
def step_summary_count(context, count, name):
    fields = {f["name"]: f["value"] for f in context.reaper_embed["fields"]}
    assert fields[name] == str(count), context.reaper_embed
