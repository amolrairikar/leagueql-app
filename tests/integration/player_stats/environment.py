import os

import boto3
from botocore.config import Config

_REQUIRED_ENV_VARS = ["AWS_ACCOUNT_ID"]


def before_all(context):
    missing = [v for v in _REQUIRED_ENV_VARS if not os.environ.get(v)]
    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing)}"
        )

    environment = os.environ.get("ENVIRONMENT", "dev")
    account_id = os.environ["AWS_ACCOUNT_ID"]
    context.s3_bucket = f"leagueql-{environment}-bucket-east-{account_id}"
    context.function_name = f"leagueql-sleeper-player-stats-refresher-{environment}"

    # A synchronous (RequestResponse) invoke blocks until the Lambda finishes,
    # which for a full refresh can approach the Lambda's 900s timeout. Raise the
    # client read timeout above that and disable retries so we wait exactly once
    # rather than re-invoking a long-running function.
    lambda_config = Config(
        read_timeout=920,
        connect_timeout=60,
        retries={"max_attempts": 0},
    )
    context.lambda_client = boto3.client(
        "lambda", region_name="us-east-1", config=lambda_config
    )
    context.s3_client = boto3.client("s3", region_name="us-east-1")


def after_scenario(context, scenario):
    # Remove the isolated test object the run wrote so the bucket is not left
    # littered with per-run integration artifacts.
    test_key = getattr(context, "test_output_key", None)
    if test_key:
        try:
            context.s3_client.delete_object(Bucket=context.s3_bucket, Key=test_key)
        except Exception:
            # Best-effort cleanup — never fail the suite on teardown.
            pass
