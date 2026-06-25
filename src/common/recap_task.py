"""Shared recap-generator Fargate task launcher for LeagueQL (BE-022).

Vendored into the processor + Stripe-webhook deployment zips. Centralizes the
``ecs:RunTask`` call that launches the recap-generator task, passing the per-league
input as container **environment overrides**. The cluster / task-definition names
and the awsvpc network config (subnets, security groups) come from env vars set by
Terraform.

``TRACE_CONTEXT`` carries W3C trace context (as a JSON string) so the task continues
the caller's OpenTelemetry trace (BE-021); it is a JSON-encoded ``{}`` when tracing
is disabled, so the contract is unchanged there.
"""

import json
import os
from typing import Any

from common.logging_utils import logger
from common.tracing import inject_context


def run_recap_task(
    ecs_client: Any,
    *,
    canonical_league_id: str,
    platform: str | None,
    correlation_id: str,
    native_league_id: str | None = None,
) -> None:
    """Launch the recap-generator Fargate task (fire-and-forget).

    No-ops (logs and returns) when the task env is not configured — e.g. the
    non-east region, where the east-only task does not exist. A failed ``RunTask``
    is swallowed so the caller (a processor run or the webhook) never fails.
    """
    cluster = os.environ.get("RECAP_TASK_CLUSTER")
    task_definition = os.environ.get("RECAP_TASK_DEFINITION")
    subnets = os.environ.get("RECAP_TASK_SUBNETS")
    security_groups = os.environ.get("RECAP_TASK_SECURITY_GROUPS")
    container = os.environ.get("RECAP_TASK_CONTAINER", "recap-generator")
    if not (cluster and task_definition and subnets and security_groups):
        logger.info("Recap task env not configured; skipping recap generation trigger")
        return

    overrides_env = [
        {"name": "CANONICAL_LEAGUE_ID", "value": canonical_league_id},
        {"name": "PLATFORM", "value": platform or ""},
        {"name": "CORRELATION_ID", "value": correlation_id or ""},
        {"name": "TRACE_CONTEXT", "value": json.dumps(inject_context({}))},
    ]
    if native_league_id:
        overrides_env.append({"name": "NATIVE_LEAGUE_ID", "value": native_league_id})

    try:
        ecs_client.run_task(
            cluster=cluster,
            taskDefinition=task_definition,
            launchType="FARGATE",
            count=1,
            networkConfiguration={
                "awsvpcConfiguration": {
                    "subnets": subnets.split(","),
                    "securityGroups": security_groups.split(","),
                    "assignPublicIp": "ENABLED",
                }
            },
            overrides={
                "containerOverrides": [
                    {"name": container, "environment": overrides_env}
                ]
            },
        )
        logger.info("Launched recap generator task for league=%s", canonical_league_id)
    except Exception as exc:
        logger.error("Failed to launch recap generator task: %s", exc)
