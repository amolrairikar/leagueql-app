import asyncio
import json
import os
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from itertools import islice
from typing import Any, Callable, Iterator

import boto3
import botocore.exceptions
import duckdb
import pandas as pd

from ai_recap import generate_recaps_for_all_seasons
from logging_utils import logger
from queries import QUERIES

s3_client = boto3.client("s3")
table_name = os.environ["DYNAMODB_TABLE_NAME"]
table = boto3.resource("dynamodb").Table(table_name)
ddb_client = boto3.client("dynamodb")
DYNAMO_BATCH_LIMIT = 25


class EntityType(str, Enum):
    TEAMS = "TEAMS"
    MATCHUPS = "MATCHUPS"
    STANDINGS = "STANDINGS"


@dataclass(frozen=True)
class KeySchema:
    pk: str
    sk: Callable  # function that builds the sort key from a row
    entity_type: EntityType


def sanitize_value(val: Any) -> Any:
    """
    Convert Python floats to Decimal for DynamoDB.

    Args:
        val: The value to sanitize.

    Returns:
        The sanitized value.
    """
    if isinstance(val, float):
        return Decimal(str(val))
    return val


def read_s3_object(bucket: str, key: str, version_id: str | None = None) -> Any:
    """
    Reads an object from S3 with the given bucket and key.

    Args:
        bucket: The S3 bucket containing the object
        key: The key corresponding to the object location within the bucket.
        version_id: Optional S3 version ID to fetch a specific version.

    Returns:
        The loaded object in JSON format.
    """
    kwargs: dict[str, Any] = {"Bucket": bucket, "Key": key}
    if version_id:
        kwargs["VersionId"] = version_id
    try:
        response = s3_client.get_object(**kwargs)
        file_content = response["Body"].read().decode("utf-8")
        return json.loads(file_content)
    except botocore.exceptions.ClientError as e:
        logger.error("Error reading raw onboarding data from S3: %s", e)
        raise e


def get_previous_version_id(bucket: str, key: str) -> str | None:
    """
    Returns the VersionId of the second-most-recent version of an S3 object,
    or None if no prior version exists.

    Args:
        bucket: The S3 bucket containing the object.
        key: The key corresponding to the object location within the bucket.

    Returns:
        The VersionId string of the previous version, or None.
    """
    try:
        response = s3_client.list_object_versions(Bucket=bucket, Prefix=key)
        versions = [v for v in response.get("Versions", []) if v["Key"] == key]
        versions.sort(key=lambda v: v["LastModified"], reverse=True)
        if len(versions) > 1:
            return versions[1]["VersionId"]
        return None
    except Exception as e:
        logger.error(f"Error fetching version history for {key}: {e}")
        return None


def resolve_seasons_to_process(
    current_seasons: list[str],
    previous_seasons: list[str] | None,
) -> list[str]:
    """
    Determines which seasons the processor should recompute.

    - No previous manifest (initial onboard): all seasons.
    - New season detected: only the new season(s).
    - Same seasons (in-season refresh): only the last season.

    Args:
        current_seasons: Ordered list of seasons from the current manifest.
        previous_seasons: Ordered list of seasons from the previous manifest,
            or None if no prior manifest exists.

    Returns:
        List of season identifiers to process.
    """
    if previous_seasons is None:
        return current_seasons
    new_seasons = sorted(set(current_seasons) - set(previous_seasons))
    if new_seasons:
        return new_seasons
    return [current_seasons[-1]]


def register_raw_data(raw_data: list[dict], con: duckdb.DuckDBPyConnection) -> None:
    """
    Register raw API response data as DuckDB views, grouped by data_type.

    Each view is named after its data_type (e.g. 'members', 'teams')
    and contains all seasons for that type.

    Args:
        raw_data: List of dicts with keys: season, data_type, data.
        con: A DuckDB connection object.
    """
    grouped: dict[str, list[dict]] = defaultdict(list)
    all_members, all_teams, all_matchups = [], [], []
    for item in raw_data:
        if item["data_type"] == "users":
            for record in item["data"].get("members", []):
                record_copy = record.copy()
                record_copy["season"] = item["season"]
                all_members.append(record_copy)
            for record in item["data"].get("teams", []):
                record_copy = record.copy()
                record_copy["season"] = item["season"]
                all_teams.append(record_copy)
        elif item["data_type"].startswith("matchups"):
            for record in item["data"].get("matchups", []):
                team_a_id = record.get("home", {}).get("teamId", "")
                team_a_score = record.get("home", {}).get("totalPoints", "0.00")
                team_b_id = record.get("away", {}).get("teamId", "")
                team_b_score = record.get("away", {}).get("totalPoints", "0.00")
                playoff_tier_type = record.get("playoffTierType", "")
                week = record.get("matchupPeriodId", "")
                if float(team_a_score) > float(team_b_score):
                    winner = team_a_id
                    loser = team_b_id
                elif float(team_b_score) > float(team_a_score):
                    winner = team_b_id
                    loser = team_a_id
                else:
                    winner = "TIE"
                    loser = "TIE"
                cleaned_matchup = {
                    "team_a_id": team_a_id,
                    "team_a_score": team_a_score,
                    "team_b_id": team_b_id,
                    "team_b_score": team_b_score,
                    "playoff_tier_type": playoff_tier_type,
                    "winner": winner,
                    "loser": loser,
                    "week": week,
                    "season": item["season"],
                }
                all_matchups.append(cleaned_matchup)

    grouped["members"] = all_members
    grouped["teams"] = all_teams
    grouped["matchups"] = all_matchups

    for data_type, rows in grouped.items():
        df = pd.DataFrame(rows)
        con.register(data_type, df)


def dataframe_to_dynamo_items(
    rel: duckdb.DuckDBPyRelation,
    schema: KeySchema,
) -> list[dict]:
    """
    Convert a DuckDB relation to a list of DynamoDB-ready items.

    Args:
        rel: A DuckDB relation (query result).
        schema: The KeySchema defining how PK/SK are constructed.

    Returns:
        List of dicts ready for boto3 put_item / batch_writer.
    """
    rows = rel.fetchall()
    columns = [desc[0] for desc in rel.description]
    row_dicts = [dict(zip(columns, row)) for row in rows]
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row_dict in row_dicts:
        sk = schema.sk(row_dict)
        grouped[sk].append({k: sanitize_value(v) for k, v in row_dict.items()})

    items = []
    for sk, group_rows in grouped.items():
        items.append(
            {
                "PK": schema.pk,
                "SK": sk,
                "data": group_rows,
            }
        )

    return items


def _chunked(iterable, size: int) -> Iterator[list]:
    it = iter(iterable)
    while chunk := list(islice(it, size)):
        yield chunk


def write_items(
    table_name: str,
    items: list[dict],
) -> None:
    """
    Batch-write items to DynamoDB, handling the 25-item limit automatically.

    Args:
        table_name: Target DynamoDB table name.
        items: List of dicts from dataframe_to_dynamo_items().
        dynamodb_resource: Optional injected boto3 resource (for testing).
    """
    for batch in _chunked(items, DYNAMO_BATCH_LIMIT):
        with table.batch_writer() as writer:
            for item in batch:
                writer.put_item(Item=item)

    logger.info("Wrote %d items to %s", len(items), table_name)


def write_metadata_items(league_id: str, refresh: bool) -> None:
    """
    Writes metadata items to DynamoDB to track onboarding/refresh status.

    Args:
        league_id: The league ID for which the metadata is being written.
        refresh: Whether this is a refresh operation (vs initial onboarding).
    """
    transact_items = []
    if refresh:
        transact_items.append(
            {
                "Update": {
                    "TableName": table.name,
                    "Key": {
                        "PK": {"S": f"LEAGUE#{league_id}"},
                        "SK": {"S": "METADATA"},
                    },
                    "UpdateExpression": "SET refresh_status = :val",
                    "ExpressionAttributeValues": {":val": {"S": "COMPLETED"}},
                }
            }
        )
    else:
        transact_items.append(
            {
                "Update": {
                    "TableName": table.name,
                    "Key": {
                        "PK": {"S": f"LEAGUE#{league_id}"},
                        "SK": {"S": "METADATA"},
                    },
                    "UpdateExpression": "SET onboarding_status = :val",
                    "ExpressionAttributeValues": {":val": {"S": "COMPLETED"}},
                }
            }
        )

    ddb_client.transact_write_items(TransactItems=transact_items)


def lambda_handler(event, context) -> None:
    """
    Main handler function for processing raw API data fetched by onboarder.

    Args:
        event: The event data that triggered the Lambda function.
        context: The context in which the Lambda function is running.
    """
    logger.info("Starting league onboarding process execution.")
    logger.info("Event data: %s", event)
    logger.info("Context data: %s", context)

    put_request_principal = event["Records"][0]["userIdentity"]["principalId"].split(
        ":"
    )[-1]
    logger.info("Put request principal: %s", put_request_principal)
    if put_request_principal == "s3-replication":
        logger.info(
            "Lambda triggered by replication event, no further processing needed."
        )

    bucket = event["Records"][0]["s3"]["bucket"]["name"]
    key = event["Records"][0]["s3"]["object"]["key"]
    canonical_league_id = key.split("/")[1]

    previous_version_id = get_previous_version_id(bucket=bucket, key=key)
    logger.info("Previous version ID for %s: %s", key, previous_version_id)

    manifest = read_s3_object(bucket=bucket, key=key)
    logger.info("Successfully read manifest file")
    platform = next(iter(manifest))
    all_seasons = manifest[platform]
    prefix = "/".join(key.split("/")[:2])

    previous_seasons = None
    if previous_version_id:
        previous_manifest = read_s3_object(
            bucket=bucket, key=key, version_id=previous_version_id
        )
        previous_seasons = previous_manifest.get(platform, [])

    seasons_to_process = resolve_seasons_to_process(
        current_seasons=all_seasons,
        previous_seasons=previous_seasons,
    )
    logger.info(
        "Seasons to process: %s (all seasons in manifest: %s)",
        seasons_to_process,
        all_seasons,
    )

    raw_data: list[dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_season = {
            executor.submit(read_s3_object, bucket, f"{prefix}/{s}.json"): s
            for s in seasons_to_process
        }
        for future in as_completed(future_to_season):
            season = future_to_season[future]
            try:
                season_data = future.result()
                raw_data.extend(season_data)
                logger.info("Successfully processed season %s", season)
            except Exception as exc:
                logger.error("Season %s generated an exception: %s", season, exc)

    con = duckdb.connect()
    register_raw_data(raw_data=raw_data, con=con)

    TEAMS_SCHEMA = KeySchema(
        pk=f"LEAGUE#{canonical_league_id}",
        sk=lambda row: f"TEAMS#{row['season']}",
        entity_type=EntityType.TEAMS,
    )

    MATCHUPS_SCHEMA = KeySchema(
        pk=f"LEAGUE#{canonical_league_id}",
        sk=lambda row: f"MATCHUPS#{row['season']}#WEEK#{int(row['week']):02d}",
        entity_type=EntityType.MATCHUPS,
    )

    STANDINGS_SCHEMA = KeySchema(
        pk=f"LEAGUE#{canonical_league_id}",
        sk=lambda row: f"STANDINGS#{row['season']}",
        entity_type=EntityType.STANDINGS,
    )

    schemas = [TEAMS_SCHEMA, MATCHUPS_SCHEMA, STANDINGS_SCHEMA]
    for schema in schemas:
        logger.info(f"Converting {schema.entity_type} data to DynamoDB items.")
        if schema in [TEAMS_SCHEMA, MATCHUPS_SCHEMA]:
            rel = con.sql(QUERIES[schema.entity_type.value][platform])
        else:
            rel = con.sql(QUERIES[schema.entity_type.value])
        con.register(f"{schema.entity_type.value}_output", rel)
        write_items(
            table_name=table_name,
            items=dataframe_to_dynamo_items(rel=rel, schema=schema),
        )

    standings_df = con.sql("SELECT * FROM STANDINGS_output").df()
    matchups_df = con.sql("SELECT * FROM MATCHUPS_output").df()

    standings_by_season: dict[str, list[dict]] = {
        season: group.to_dict("records")
        for season, group in standings_df.groupby("season")
    }
    matchups_by_season: dict[str, list[dict]] = {
        season: group.to_dict("records")
        for season, group in matchups_df.groupby("season")
    }

    write_metadata_items(
        league_id=canonical_league_id, refresh=previous_version_id is not None
    )

    try:
        asyncio.run(
            generate_recaps_for_all_seasons(
                table=table,
                api_key=os.environ["ANTHROPIC_API_KEY"],
                pk=f"LEAGUE#{canonical_league_id}",
                seasons=seasons_to_process,
                standings_by_season=standings_by_season,
                matchups_by_season=matchups_by_season,
            )
        )
    except Exception as e:
        logger.error("AI recap generation failed: %s", e)
        # Do not re-raise — recap failure should not fail the processor run
