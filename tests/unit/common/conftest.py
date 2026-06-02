import os

# common.job_status creates a boto3 DynamoDB client at import time; ensure a
# region is set so client construction succeeds in CI (no network is made).
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
