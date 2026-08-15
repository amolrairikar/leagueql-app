import os

import boto3

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
    context.cluster = f"leagueql-{environment}"
    context.task_family = f"leagueql-sleeper-player-stats-refresher-{environment}"
    context.container_name = "sleeper-player-stats-refresher"

    context.ecs_client = boto3.client("ecs", region_name="us-east-1")
    context.ec2_client = boto3.client("ec2", region_name="us-east-1")
    context.s3_client = boto3.client("s3", region_name="us-east-1")

    # Discover the shared outbound-only Fargate networking by tag (created in the
    # aws-account-management repo), the same way the Terraform data sources do.
    vpcs = context.ec2_client.describe_vpcs(
        Filters=[{"Name": "tag:Name", "Values": ["leagueql-fargate-vpc"]}]
    )["Vpcs"]
    assert vpcs, "Could not find the leagueql-fargate-vpc"
    vpc_id = vpcs[0]["VpcId"]

    subnets = context.ec2_client.describe_subnets(
        Filters=[
            {"Name": "vpc-id", "Values": [vpc_id]},
            {"Name": "tag:tier", "Values": ["public"]},
        ]
    )["Subnets"]
    context.subnet_ids = [s["SubnetId"] for s in subnets]

    sgs = context.ec2_client.describe_security_groups(
        Filters=[
            {"Name": "vpc-id", "Values": [vpc_id]},
            {"Name": "tag:Name", "Values": ["leagueql-fargate-task-sg"]},
        ]
    )["SecurityGroups"]
    context.security_group_ids = [g["GroupId"] for g in sgs]


def after_scenario(context, scenario):
    # Remove the isolated test object the run wrote so the bucket is not left
    # littered with per-run integration artifacts.
    test_key = getattr(context, "test_output_key", None)
    if test_key:
        try:
            context.s3_client.delete_object(Bucket=context.s3_bucket, Key=test_key)
        except Exception:  # noqa: S110 — best-effort teardown cleanup, intentionally swallowed
            # Best-effort cleanup — never fail the suite on teardown.
            pass
