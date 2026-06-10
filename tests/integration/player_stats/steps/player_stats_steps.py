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
    "season, player-cap, and output-key overrides for the player stats refresher task"
)
def step_build_overrides(context):
    context.season = _most_recent_completed_season()
    context.test_output_key = TEST_OUTPUT_S3_KEY
    # Snapshot the production cache so we can assert it is untouched afterward.
    context.prod_cache_fingerprint = _production_cache_fingerprint(context)
    # Container env-var overrides that drive a deterministic, capped refresh into an
    # isolated test key regardless of the live NFL state. The scheduled task sets none
    # of these and keeps full production behavior.
    context.env_overrides = [
        {"name": "SEASON", "value": context.season},
        {"name": "MAX_PLAYERS", "value": str(MAX_PLAYERS)},
        {"name": "OUTPUT_KEY", "value": TEST_OUTPUT_S3_KEY},
    ]


@when("the deployed player stats refresher task is run to completion")
def step_run_task(context):
    response = context.ecs_client.run_task(
        cluster=context.cluster,
        taskDefinition=context.task_family,
        launchType="FARGATE",
        count=1,
        networkConfiguration={
            "awsvpcConfiguration": {
                "subnets": context.subnet_ids,
                "securityGroups": context.security_group_ids,
                "assignPublicIp": "ENABLED",
            }
        },
        overrides={
            "containerOverrides": [
                {
                    "name": context.container_name,
                    "environment": context.env_overrides,
                }
            ]
        },
    )
    failures = response.get("failures", [])
    assert not failures, f"RunTask failed: {failures}"
    task_arn = response["tasks"][0]["taskArn"]

    # Block until the task stops. A capped run is fast (~MAX_PLAYERS requests) plus
    # task startup/image pull, so allow up to ~10 minutes.
    waiter = context.ecs_client.get_waiter("tasks_stopped")
    waiter.wait(
        cluster=context.cluster,
        tasks=[task_arn],
        WaiterConfig={"Delay": 15, "MaxAttempts": 40},
    )
    described = context.ecs_client.describe_tasks(
        cluster=context.cluster, tasks=[task_arn]
    )
    context.task = described["tasks"][0]


@then("the task completes with a zero exit code")
def step_assert_task_ok(context):
    container = next(
        c for c in context.task["containers"] if c["name"] == context.container_name
    )
    exit_code = container.get("exitCode")
    assert exit_code == 0, (
        f"Task stopped with exit code {exit_code}: "
        f"stopCode={context.task.get('stopCode')} "
        f"reason={context.task.get('stoppedReason')} "
        f"containerReason={container.get('reason')}"
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
