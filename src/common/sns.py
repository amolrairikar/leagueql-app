"""Shared SNS failure-alert publishing for LeagueQL Lambda functions.

Vendored into every function's deployment zip. A single SNS client is created
from the ``SNS_TOPIC_ARN`` env var; when that var is unset the client is ``None``
and :func:`publish_failure` becomes a no-op. Each service binds its own ``subject``
(e.g. via ``functools.partial``) so alerts identify which Lambda failed.
"""

import os

import boto3
import botocore.config

from common.logging_utils import correlation_id_var, logger

_retry_config = botocore.config.Config(retries={"mode": "standard"})
_sns_topic_arn = os.environ.get("SNS_TOPIC_ARN")
_sns_client = boto3.client("sns", config=_retry_config) if _sns_topic_arn else None


def publish_failure(error_message: str, subject: str) -> None:
    """
    Publish a failure alert to SNS; no-op when SNS is not configured.

    Args:
        error_message: The error detail to include in the alert body.
        subject: The SNS subject line identifying the failing service.
    """
    if not _sns_client:
        return
    try:
        _sns_client.publish(
            TopicArn=_sns_topic_arn,
            Subject=subject,
            Message=f"Correlation ID: {correlation_id_var.get()}\nError: {error_message}",
        )
    except Exception:
        logger.warning("Failed to publish SNS failure notification", exc_info=True)
