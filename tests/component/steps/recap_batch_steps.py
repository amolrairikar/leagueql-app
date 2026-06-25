"""Steps for the AI weekly matchup recap batch pipeline component test (BE-022)."""

import json
from unittest.mock import patch

from behave import given, then, when
from boto3.dynamodb.conditions import Key
from common_steps import get_item, put_item

# Fixed job ARN the patched ``submit_batch_job`` returns, so the manifest key and the
# simulated completion event line up across steps.
JOB_ARN = "arn:aws:bedrock:us-east-1:000000000000:model-invocation-job/comptest"


def _matchup(week2: str) -> dict:
    """One minimal normal matchup row (ints only — the resource Table rejects float)."""
    return {
        "team_a_id": "1",
        "team_a_display_name": "alice",
        "team_a_team_name": "Alice's Team",
        "team_a_score": 120,
        "team_a_starters": [
            {"full_name": "QB One", "position": "QB", "points_scored": 30},
        ],
        "team_a_bench": [],
        "team_b_id": "2",
        "team_b_display_name": "bob",
        "team_b_team_name": "Bob's Team",
        "team_b_score": 90,
        "team_b_starters": [],
        "team_b_bench": [],
        "playoff_round": None,
        "winner": "1",
        "loser": "2",
        "week": week2,
        "season": "0000",
    }


def _seed_season(context, canonical: str, season: str, weeks: list[str]) -> None:
    for week2 in weeks:
        put_item(
            context,
            {
                "PK": f"LEAGUE#{canonical}",
                "SK": f"MATCHUPS#{season}#WEEK#{week2}",
                "data": [_matchup(week2)],
            },
        )
    put_item(
        context,
        {
            "PK": f"LEAGUE#{canonical}",
            "SK": f"STANDINGS#{season}",
            "data": [
                {"team_id": "1", "record": "1-0-0"},
                {"team_id": "2", "record": "0-1-0"},
            ],
        },
    )


@given('a premium league "{canonical}" with matchups for seasons "{seasons}"')
def step_seed_premium_league(context, canonical, seasons):
    season_list = [s.strip() for s in seasons.split(",")]
    # LEAGUE_LOOKUP carries the seasons set read via GSI1 for season enumeration.
    put_item(
        context,
        {
            "PK": "LEAGUE#100#PLATFORM#SLEEPER",
            "SK": "LEAGUE_LOOKUP",
            "canonical_league_id": canonical,
            "seasons": set(season_list),
            "platform": "SLEEPER",
            "league_id": "100",
        },
    )
    # Premium METADATA (far-future subscription) so the server-side gate passes.
    put_item(
        context,
        {
            "PK": f"LEAGUE#{canonical}",
            "SK": "METADATA",
            "platform": "SLEEPER",
            "league_name": "Recap League",
            "subscription_end_time": "2999-01-01T00:00:00+00:00",
        },
    )
    # First two seasons get 2 weeks / 1 week so "all weeks of all seasons" is
    # meaningfully exercised; extra seasons (if any) get a single week.
    for i, season in enumerate(season_list):
        weeks = ["01", "02"] if i == 0 else ["01"]
        _seed_season(context, canonical, season, weeks)


@given('a pending recap marker for league "{canonical}"')
def step_seed_marker(context, canonical):
    put_item(
        context,
        {
            "PK": "RECAP_QUEUE",
            "SK": f"PENDING#{canonical}",
            "canonical_league_id": canonical,
            "platform": "SLEEPER",
            "status": "pending",
        },
    )


@when("the recap drainer runs")
def step_run_drainer(context):
    with patch.object(
        context.recap_drainer, "submit_batch_job", return_value=JOB_ARN
    ) as spy:
        context.drainer_result = context.recap_drainer._handle()
    context.drainer_submit = spy


@when("Bedrock finishes the batch job")
def step_bedrock_finishes(context):
    """Simulate Bedrock writing one output record per input record to the job's S3
    output prefix (the manifest records exactly which records were submitted)."""
    manifest = get_item(context, f"RECAP_JOB#{JOB_ARN}", "MANIFEST")
    assert manifest, "drainer wrote no job manifest"
    bucket, _, prefix = manifest["output_uri"][len("s3://") :].partition("/")
    lines = [
        json.dumps(
            {
                "recordId": record_id,
                "modelOutput": {"generation": "Big Week\n\nPara one.\n\nPara two."},
            }
        )
        for record_id in manifest["records"]
    ]
    context.s3.put_object(
        Bucket=bucket,
        Key=prefix + "records.jsonl.out",
        Body="\n".join(lines).encode("utf-8"),
    )


@when("the recap completion runs for the job")
def step_run_completion(context):
    event = {"detail": {"batchJobArn": JOB_ARN, "status": "Completed"}}
    context.completion_result = context.recap_completion._handle(event)


@given('the recap batch pipeline has fully run for league "{canonical}"')
def step_full_pipeline(context, canonical):
    step_run_drainer(context)
    step_bedrock_finishes(context)
    step_run_completion(context)


@then(
    'a MATCHUP_RECAP item exists for league "{canonical}" season "{season}" '
    'week "{week2}"'
)
def step_recap_item_exists(context, canonical, season, week2):
    item = get_item(
        context, f"LEAGUE#{canonical}", f"MATCHUP_RECAP#{season}#WEEK#{week2}"
    )
    assert item, f"no recap item for {season} week {week2}"
    recap = item["data"][0]
    assert recap["headline"], "recap headline missing"
    assert recap["body"], "recap body missing"
    assert recap["model"] == "us.meta.llama3-3-70b-instruct-v1:0"


@then('no MATCHUP_RECAP items exist for league "{canonical}"')
def step_no_recap_items(context, canonical):
    table = context.ddb_resource.Table(context.table_name)
    resp = table.query(
        KeyConditionExpression=Key("PK").eq(f"LEAGUE#{canonical}")
        & Key("SK").begins_with("MATCHUP_RECAP#")
    )
    assert not resp.get("Items"), "expected no recap items"


@then("the recap drainer submitted a job for {count:d} records")
def step_drainer_submitted(context, count):
    assert context.drainer_result["status"] == "submitted", context.drainer_result
    assert context.drainer_result["records"] == count, context.drainer_result


@then("the recap drainer submitted no job")
def step_drainer_no_job(context):
    assert context.drainer_result["status"] != "submitted", context.drainer_result


@then('the recap queue marker for league "{canonical}" is cleared')
def step_marker_cleared(context, canonical):
    assert not get_item(context, "RECAP_QUEUE", f"PENDING#{canonical}"), (
        "expected the pending recap marker to be cleared"
    )


@then("the recap generator was invoked after processing")
def step_recap_invoked_after_processing(context):
    # BE-022: the processor enqueues a pending-recap marker at end of run (the shared
    # enqueue spy stands in for the real record_pending_recap DynamoDB write).
    assert context.recap_enqueue_spy.called, (
        "recap enqueue was not called at end of processing"
    )
