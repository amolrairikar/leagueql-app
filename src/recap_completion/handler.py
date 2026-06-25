"""AI weekly matchup recap completion — EventBridge Lambda for LeagueQL (BE-022).

Triggered by the Bedrock *Batch Inference Job State Change* event for jobs the
recap-drainer submitted. On a terminal state it reconciles the job:

- **Completed:** read the job's output JSONL from S3, parse each ``modelOutput`` into a
  recap, and write the ``MATCHUP_RECAP#{season}#WEEK#{week}`` item (idempotent — skip
  if already present), routing each output record back to its ``(league, season,
  week)`` via the ``RECAP_JOB`` manifest. Then delete the manifest and the contributing
  leagues' ``in_flight`` queue markers.
- **PartiallyCompleted:** write whatever outputs exist, then **reset** the markers to
  ``pending`` so the drainer refills the still-missing weeks (idempotent skip leaves the
  written ones alone).
- **Failed / Stopped / Expired:** no outputs; reset the markers to ``pending`` for the
  next drain to resubmit, delete the manifest, and raise an SNS alert.

Marker deletes/resets are **conditional on the marker still pointing at this job**, so a
newer job that re-flipped a league is never disturbed. Roots its own trace (BE-021).
"""

import datetime
import json
import os

import boto3
import botocore.config
from botocore.exceptions import ClientError

from common.bedrock import parse_recap_output
from common.logging_utils import logger
from common.sns import publish_failure
from common.tracing import init_tracing, traced_handler

init_tracing("leagueql-recap-completion")

_retry_config = botocore.config.Config(retries={"mode": "standard"})
_table_name = os.environ["DYNAMODB_TABLE_NAME"]
_table = boto3.resource("dynamodb", config=_retry_config).Table(_table_name)
_s3 = boto3.client("s3", config=_retry_config)

_QUEUE_PK = "RECAP_QUEUE"
_ALERT_SUBJECT = "LeagueQL recap batch job failed"

_SUCCESS_STATES = {"Completed", "PartiallyCompleted"}
_FAILURE_STATES = {"Failed", "Stopped", "Expired"}


def lambda_handler(event, context):  # pragma: no cover - thin entrypoint
    with traced_handler("recap_completion.handle", root=True):
        result = _handle(event)
    logger.info("Recap completion finished: %s", result)
    return result


def _handle(event) -> dict:
    detail = event.get("detail", {}) if isinstance(event, dict) else {}
    job_arn = detail.get("batchJobArn") or detail.get("jobArn")
    status = detail.get("status")
    if not job_arn or not status:
        logger.warning("Recap completion event missing job ARN or status; ignoring")
        return {"status": "ignored", "reason": "malformed_event"}

    if status not in _SUCCESS_STATES and status not in _FAILURE_STATES:
        logger.info("Ignoring non-terminal recap job state %s for %s", status, job_arn)
        return {"status": "ignored", "reason": f"non_terminal:{status}"}

    manifest = _get_manifest(job_arn)
    if not manifest:
        logger.warning("No manifest for recap job %s; nothing to reconcile", job_arn)
        return {"status": "ignored", "reason": "no_manifest"}

    league_ids = manifest.get("league_ids", [])

    if status in _FAILURE_STATES:
        logger.error("Recap batch job %s ended in state %s", job_arn, status)
        publish_failure(f"Batch job {job_arn} ended in state {status}", _ALERT_SUBJECT)
        for league in league_ids:
            _reset_marker(league, job_arn)
        _delete_manifest(job_arn)
        return {"status": "failed", "job_state": status, "leagues": len(league_ids)}

    written = _write_outputs(manifest)

    if status == "PartiallyCompleted":
        for league in league_ids:
            _reset_marker(league, job_arn)
    else:  # Completed
        for league in league_ids:
            _delete_marker(league, job_arn)
    _delete_manifest(job_arn)

    return {"status": "completed", "job_state": status, "written": written}


def _write_outputs(manifest: dict) -> int:
    """Read the job's output JSONL from S3 and write each recap idempotently."""
    routing = manifest.get("records", {})
    model = manifest.get("model", "")
    bucket, prefix = _split_s3_uri(manifest["output_uri"])

    written = 0
    for key in _list_output_keys(bucket, prefix):
        body = _s3.get_object(Bucket=bucket, Key=key)["Body"].read().decode("utf-8")
        for line in body.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except ValueError:
                logger.warning("Skipping unparsable output line in %s", key)
                continue
            if _write_record(record, routing, model):
                written += 1
    logger.info("Wrote %d recap(s) from job output", written)
    return written


def _write_record(record: dict, routing: dict, model: str) -> bool:
    """Write one output record's recap. Returns True if a new item was written."""
    record_id = record.get("recordId")
    target = routing.get(record_id)
    if not target:
        logger.warning("Output record %s not in manifest; skipping", record_id)
        return False
    model_output = record.get("modelOutput")
    if not model_output or record.get("error"):
        logger.warning(
            "Output record %s has no usable modelOutput; skipping", record_id
        )
        return False

    recap = parse_recap_output(model_output)
    if not recap.get("headline") and not recap.get("body"):
        logger.warning("Output record %s parsed empty; skipping", record_id)
        return False

    season = target["season"]
    week = target["week"]
    try:
        _table.put_item(
            Item={
                "PK": f"LEAGUE#{target['canonical_league_id']}",
                "SK": f"MATCHUP_RECAP#{season}#WEEK#{week}",
                "data": [
                    {
                        "headline": recap["headline"],
                        "body": recap["body"],
                        "generated_at": _now_iso(),
                        "model": model,
                    }
                ],
            },
            ConditionExpression="attribute_not_exists(SK)",
        )
        return True
    except ClientError as exc:
        if (
            exc.response.get("Error", {}).get("Code")
            == "ConditionalCheckFailedException"
        ):
            return False  # already written — idempotent
        raise


# --- Manifest + markers ----------------------------------------------------------


def _get_manifest(job_arn: str) -> dict:
    resp = _table.get_item(Key={"PK": f"RECAP_JOB#{job_arn}", "SK": "MANIFEST"})
    return resp.get("Item", {})


def _delete_manifest(job_arn: str) -> None:
    _table.delete_item(Key={"PK": f"RECAP_JOB#{job_arn}", "SK": "MANIFEST"})


def _delete_marker(canonical_league_id: str, job_arn: str) -> None:
    """Delete a league's marker only if it still points at this job."""
    _conditional_marker_op(
        canonical_league_id,
        job_arn,
        update=None,
    )


def _reset_marker(canonical_league_id: str, job_arn: str) -> None:
    """Reset a league's marker to ``pending`` only if it still points at this job."""
    _conditional_marker_op(
        canonical_league_id,
        job_arn,
        update="SET #s = :pending REMOVE job_id, submitted_at",
    )


def _conditional_marker_op(
    canonical_league_id: str, job_arn: str, update: str | None
) -> None:
    key = {"PK": _QUEUE_PK, "SK": f"PENDING#{canonical_league_id}"}
    condition = "job_id = :job"
    values = {":job": job_arn}
    try:
        if update is None:
            _table.delete_item(
                Key=key,
                ConditionExpression=condition,
                ExpressionAttributeValues=values,
            )
        else:
            _table.update_item(
                Key=key,
                UpdateExpression=update,
                ConditionExpression=condition,
                ExpressionAttributeNames={"#s": "status"},
                ExpressionAttributeValues={**values, ":pending": "pending"},
            )
    except ClientError as exc:
        if (
            exc.response.get("Error", {}).get("Code")
            == "ConditionalCheckFailedException"
        ):
            # Marker was re-enqueued / re-submitted under a newer job; leave it.
            logger.info(
                "Recap marker for league=%s no longer points at job %s; leaving it",
                canonical_league_id,
                job_arn,
            )
            return
        raise


# --- S3 helpers ------------------------------------------------------------------


def _split_s3_uri(uri: str) -> tuple[str, str]:
    without_scheme = uri[len("s3://") :] if uri.startswith("s3://") else uri
    bucket, _, prefix = without_scheme.partition("/")
    return bucket, prefix


def _list_output_keys(bucket: str, prefix: str) -> list[str]:
    """List the ``.out`` output objects Bedrock wrote under the job's output prefix."""
    keys: list[str] = []
    token = None
    while True:
        kwargs = {"Bucket": bucket, "Prefix": prefix}
        if token:
            kwargs["ContinuationToken"] = token
        resp = _s3.list_objects_v2(**kwargs)
        for obj in resp.get("Contents", []):
            key = obj["Key"]
            if key.endswith(".out") or key.endswith(".jsonl.out"):
                keys.append(key)
        if not resp.get("IsTruncated"):
            break
        token = resp.get("NextContinuationToken")
    return keys


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()
