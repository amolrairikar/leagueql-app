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

from logging_utils import logger
from queries import QUERIES

s3_client = boto3.client("s3")
table_name = os.environ["DYNAMODB_TABLE_NAME"]
table = boto3.resource("dynamodb").Table(table_name)
ddb_client = boto3.client("dynamodb")
DYNAMO_BATCH_LIMIT = 25

ESPN_POSITION_ID_MAPPING = {
    1: "QB",
    2: "RB",
    3: "WR",
    4: "TE",
    5: "K",
    16: "D/ST",
}

ESPN_FANTASY_POSITION_ID_MAPPING = {
    0: "QB",
    2: "RB",
    4: "WR",
    6: "TE",
    16: "D/ST",
    17: "K",
    23: "FLEX",
}


class EntityType(str, Enum):
    TEAMS = "TEAMS"
    MATCHUPS = "MATCHUPS"
    STANDINGS = "STANDINGS"
    PLAYOFF_BRACKET = "PLAYOFF_BRACKET"


@dataclass(frozen=True)
class KeySchema:
    pk: str
    sk: Callable  # function that builds the sort key from a row
    entity_type: EntityType


def compile_espn_bench_stats(roster: dict, starter_ids: list[int]) -> list[dict]:
    """
    Build a list of stat dicts for every bench player in an ESPN roster.

    Args:
        roster: The ESPN roster object containing an 'entries' list of player dicts.
        starter_ids: Player IDs already counted as starters, excluded from bench output.

    Returns:
        List of dicts with player_id, full_name, points_scored, and position.
    """
    stats = []
    for player in roster.get("entries", []):
        player_id = player["playerId"]
        if player_id in starter_ids:
            continue
        stats.append(
            {
                "player_id": player_id,
                "full_name": player["playerPoolEntry"]["player"]["fullName"],
                "points_scored": player["playerPoolEntry"]["appliedStatTotal"],
                "position": ESPN_POSITION_ID_MAPPING[
                    player["playerPoolEntry"]["player"]["defaultPositionId"]
                ],
            }
        )
    return stats


def compile_espn_starter_stats(
    roster: dict, slot_map: dict[int, int]
) -> tuple[list[dict], list[int]]:
    """
    Build a list of stat dicts for every starter in an ESPN roster.

    Args:
        roster: The ESPN roster object containing an 'entries' list of player dicts.
        slot_map: Mapping of player ID to lineup slot ID derived from the scoring-period roster,
            used to resolve each player's actual fantasy position.

    Returns:
        Tuple of (stats, ids) where stats is a list of dicts with player_id, full_name,
        points_scored, position, and fantasy_position, and ids is the list of starter player IDs.
    """
    stats = []
    ids = []
    for player in roster.get("entries", []):
        player_id = player["playerId"]
        if player_id in slot_map:
            lineup_slot_id = slot_map[player_id]
        else:
            eligible_slots = player["playerPoolEntry"]["player"].get(
                "eligibleSlots", []
            )
            lineup_slot_id = next(
                (s for s in eligible_slots if s in ESPN_FANTASY_POSITION_ID_MAPPING),
                player["lineupSlotId"],
            )
        stats.append(
            {
                "player_id": player_id,
                "full_name": player["playerPoolEntry"]["player"]["fullName"],
                "points_scored": player["playerPoolEntry"]["appliedStatTotal"],
                "position": ESPN_POSITION_ID_MAPPING[
                    player["playerPoolEntry"]["player"]["defaultPositionId"]
                ],
                "fantasy_position": ESPN_FANTASY_POSITION_ID_MAPPING.get(
                    lineup_slot_id, "FLEX"
                ),
            }
        )
        ids.append(player_id)
    return stats, ids


def compile_sleeper_starter_stats(
    starters: list[str], starters_points: list[float], player_metadata: dict
) -> tuple[list[dict], list[str]]:
    """
    Build a list of stat dicts for every starter in a Sleeper roster.

    Args:
        starters: Ordered list of starter player IDs.
        starters_points: Points scored by each starter, in the same order as starters.
        player_metadata: Mapping of player ID to metadata dict (full_name, position, etc.).

    Returns:
        Tuple of (stats, ids) where stats is a list of dicts with player_id and
        points_scored, and ids is the list of starter player IDs.
    """
    stats = [
        {
            "player_id": player_id,
            "full_name": player_metadata.get(player_id, {}).get("full_name"),
            "points_scored": points,
            "position": player_metadata.get(player_id, {}).get("position"),
            "fantasy_position": None,
        }
        for player_id, points in zip(starters, starters_points)
    ]
    return stats, starters


def compile_sleeper_bench_stats(
    players: list[str],
    players_points: dict[str, float],
    starter_ids: list[str],
    player_metadata: dict,
) -> list[dict]:
    """
    Build a list of stat dicts for every bench player in a Sleeper roster.

    Args:
        players: Full list of player IDs on the roster (starters + bench).
        players_points: Mapping of player ID to points scored.
        starter_ids: Player IDs already counted as starters, excluded from bench output.
        player_metadata: Mapping of player ID to metadata dict (full_name, position, etc.).

    Returns:
        List of dicts with player_id and points_scored.
    """
    return [
        {
            "player_id": player_id,
            "full_name": player_metadata.get(player_id, {}).get("full_name"),
            "points_scored": players_points.get(player_id, 0.0),
            "position": player_metadata.get(player_id, {}).get("position"),
        }
        for player_id in players
        if player_id not in starter_ids
    ]


def sanitize_value(val: Any) -> Any:
    """
    Recursively convert floats to Decimal so values are safe for DynamoDB.

    Args:
        val: Any value — scalar, list, or dict.

    Returns:
        The value with all floats replaced by their Decimal equivalents.
    """
    if isinstance(val, float):
        return Decimal(str(val))
    if isinstance(val, list):
        return [sanitize_value(v) for v in val]
    if isinstance(val, dict):
        return {k: sanitize_value(v) for k, v in val.items()}
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


def _build_espn_brackets(all_matchups: list[dict]) -> list[dict]:
    """
    Derive a bracket structure from ESPN playoff matchup data.

    Builds bracket entries equivalent to the Sleeper bracket format, with match IDs,
    round numbers, and team_from relationships linking each round to the previous one.

    Bye matchups (team_b_id empty) are skipped — bye teams appear with null team_from
    in the next round, which the frontend uses to detect and render the bye card.

    Final-round positions: WB final = 1 (championship); consolation finals = 3 or 5
    based on whether both teams came from WB losses (3rd place) or consolation (5th place).

    Args:
        all_matchups: List of ESPN matchup dicts already built by _register_espn_raw_data.

    Returns:
        List of bracket entry dicts with match_id, round, team_1, team_2, winner, loser,
        position, team_1_from, team_2_from, and season.
    """
    playoff_types = {"WINNERS_BRACKET", "WINNERS_CONSOLATION_LADDER"}
    playoff_matchups = [
        m for m in all_matchups if m["playoff_tier_type"] in playoff_types
    ]

    by_season: dict[str, list[dict]] = defaultdict(list)
    for m in playoff_matchups:
        by_season[m["season"]].append(m)

    all_brackets: list[dict] = []
    for season, matchups in by_season.items():
        unique_weeks = sorted({int(m["week"]) for m in matchups})
        week_to_round = {w: i + 1 for i, w in enumerate(unique_weeks)}
        matchups.sort(key=lambda x: (int(x["week"]), str(x["team_a_id"])))

        match_id_counter = 1
        team_round_result: dict[tuple[str, int], tuple[int, str]] = {}
        match_id_to_type: dict[int, str] = {}
        bracket_entries: list[dict] = []

        for matchup in matchups:
            team_1 = str(matchup["team_a_id"])
            team_2 = str(matchup["team_b_id"])
            if not team_2:
                continue  # skip bye matchups — bye teams get null team_from in the next round

            round_num = week_to_round[int(matchup["week"])]
            match_id = match_id_counter
            match_id_counter += 1

            raw_winner = str(matchup["winner"])
            raw_loser = str(matchup["loser"])
            winner = raw_winner if raw_winner not in ("TIE", "") else None
            loser = raw_loser if raw_loser not in ("TIE", "") else None

            if winner == team_1:
                team_round_result[(team_1, round_num)] = (match_id, "w")
                team_round_result[(team_2, round_num)] = (match_id, "l")
            elif winner == team_2:
                team_round_result[(team_2, round_num)] = (match_id, "w")
                team_round_result[(team_1, round_num)] = (match_id, "l")

            is_wb = matchup["playoff_tier_type"] == "WINNERS_BRACKET"
            match_id_to_type[match_id] = "WB" if is_wb else "CONSOLATION"
            bracket_entries.append(
                {
                    "match_id": match_id,
                    "round": round_num,
                    "team_1": team_1,
                    "team_2": team_2,
                    "winner": winner,
                    "loser": loser,
                    "position": None if is_wb else 2,
                    "team_1_from": None,
                    "team_2_from": None,
                    "season": season,
                }
            )

        for entry in bracket_entries:
            if entry["round"] > 1:
                prev_round = entry["round"] - 1
                for team_key, from_key in [
                    ("team_1", "team_1_from"),
                    ("team_2", "team_2_from"),
                ]:
                    team_id = entry[team_key]
                    if team_id:
                        result = team_round_result.get((team_id, prev_round))
                        if result:
                            prev_match_id, outcome = result
                            entry[from_key] = json.dumps({outcome: prev_match_id})

        if bracket_entries:
            max_round = max(e["round"] for e in bracket_entries)
            for entry in bracket_entries:
                if entry["round"] != max_round:
                    continue
                if entry["position"] is None:
                    entry["position"] = 1  # WB final = championship
                else:
                    # Consolation final: 3rd place if both teams came from WB losses, else 5th
                    from_types = []
                    for from_key in ("team_1_from", "team_2_from"):
                        from_str = entry.get(from_key)
                        if from_str:
                            parsed = json.loads(from_str)
                            mid = parsed.get("w") or parsed.get("l")
                            if mid is not None:
                                from_types.append(
                                    match_id_to_type.get(mid, "CONSOLATION")
                                )
                    entry["position"] = (
                        3 if from_types and all(t == "WB" for t in from_types) else 5
                    )

        all_brackets.extend(bracket_entries)

    return all_brackets


def _register_espn_raw_data(
    raw_data: list[dict],
) -> dict[str, list[dict]]:
    """
    Parse raw ESPN API data into grouped lists ready for DuckDB registration.

    Extracts members and teams from 'users' records and builds cleaned matchup
    dicts (including starter/bench player stats) from 'matchups*' records.

    Args:
        raw_data: List of dicts with keys: season, data_type, data.

    Returns:
        Dict with keys 'members', 'teams', 'matchups', and 'brackets', each mapping to a list of row dicts.
    """
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

                team_a_starters = record.get("home", {}).get(
                    "rosterForMatchupPeriod", {}
                )
                team_a_bench = record.get("home", {}).get(
                    "rosterForCurrentScoringPeriod", {}
                )
                team_b_starters = record.get("away", {}).get(
                    "rosterForMatchupPeriod", {}
                )
                team_b_bench = record.get("away", {}).get(
                    "rosterForCurrentScoringPeriod", {}
                )
                team_a_slot_map = {
                    p["playerId"]: p["lineupSlotId"]
                    for p in team_a_bench.get("entries", [])
                }
                team_b_slot_map = {
                    p["playerId"]: p["lineupSlotId"]
                    for p in team_b_bench.get("entries", [])
                }
                team_a_starters_stats, team_a_starters_ids = compile_espn_starter_stats(
                    roster=team_a_starters, slot_map=team_a_slot_map
                )
                team_b_starters_stats, team_b_starters_ids = compile_espn_starter_stats(
                    roster=team_b_starters, slot_map=team_b_slot_map
                )
                team_a_bench_stats = compile_espn_bench_stats(
                    roster=team_a_bench, starter_ids=team_a_starters_ids
                )
                team_b_bench_stats = compile_espn_bench_stats(
                    roster=team_b_bench, starter_ids=team_b_starters_ids
                )

                all_matchups.append(
                    {
                        "team_a_id": team_a_id,
                        "team_a_score": team_a_score,
                        "team_a_starters": team_a_starters_stats,
                        "team_a_bench": team_a_bench_stats,
                        "team_b_id": team_b_id,
                        "team_b_score": team_b_score,
                        "team_b_starters": team_b_starters_stats,
                        "team_b_bench": team_b_bench_stats,
                        "playoff_tier_type": playoff_tier_type,
                        "winner": winner,
                        "loser": loser,
                        "week": week,
                        "season": item["season"],
                    }
                )

    brackets = _build_espn_brackets(all_matchups)
    return {
        "members": all_members,
        "teams": all_teams,
        "matchups": all_matchups,
        "brackets": brackets,
    }


def _register_sleeper_raw_data(
    raw_data: list[dict],
    player_metadata: dict,
) -> dict[str, list[dict]]:
    """
    Parse raw Sleeper API data into grouped lists ready for DuckDB registration.

    Args:
        raw_data: List of dicts with keys: season, data_type, data.
        player_metadata: Mapping of Sleeper player ID to metadata dict (full_name, position, etc.).

    Returns:
        Dict with keys 'users', 'rosters', and 'matchups', each mapping to a list of row dicts.
    """
    bracket_by_season: dict[str, dict[frozenset, dict]] = defaultdict(dict)
    all_brackets: list[dict] = []
    for item in raw_data:
        if item["data_type"] in ("playoff_bracket", "losers_bracket"):
            for entry in item["data"]:
                t1, t2 = entry.get("t1"), entry.get("t2")
                if t1 is None or t2 is None:
                    continue
                p = entry.get("p")
                if item["data_type"] == "losers_bracket":
                    tier = "LOSERS_BRACKET"
                else:
                    tier = (
                        "WINNERS_BRACKET" if (p is None or p == 1) else "LOSERS_BRACKET"
                    )
                bracket_by_season[item["season"]][frozenset([t1, t2])] = {
                    "tier": tier,
                }
                all_brackets.append(
                    {
                        "match_id": entry.get("m"),
                        "round": entry.get("r"),
                        "team_1": t1,
                        "team_2": t2,
                        "winner": entry.get("w"),
                        "loser": entry.get("l"),
                        "position": p,
                        "bracket_type": "LOSERS_BRACKET"
                        if item["data_type"] == "losers_bracket"
                        else "WINNERS_BRACKET",
                        "team_1_from": json.dumps(entry["t1_from"])
                        if "t1_from" in entry
                        else None,
                        "team_2_from": json.dumps(entry["t2_from"])
                        if "t2_from" in entry
                        else None,
                        "season": item["season"],
                    }
                )

    all_users, all_rosters, all_matchups = [], [], []
    for item in raw_data:
        if item["data_type"] == "users":
            for record in item["data"]:
                record_copy = record.copy()
                record_copy["season"] = item["season"]
                all_users.append(record_copy)
        elif item["data_type"] == "rosters":
            for record in item["data"]:
                record_copy = record.copy()
                record_copy["season"] = item["season"]
                all_rosters.append(record_copy)
        elif item["data_type"].startswith("matchups"):
            bracket = bracket_by_season[item["season"]]
            season = item["season"]
            week = int(item["data_type"].split("week")[1])
            paired: dict[int, list[dict]] = defaultdict(list)
            for entry in item["data"]:
                paired[entry["matchup_id"]].append(entry)
            for _, teams in paired.items():
                if len(teams) != 2:
                    continue
                team_a, team_b = teams[0], teams[1]
                team_a_score = team_a.get("points", 0.0)
                team_b_score = team_b.get("points", 0.0)
                if float(team_a_score) > float(team_b_score):
                    winner = team_a["roster_id"]
                    loser = team_b["roster_id"]
                elif float(team_b_score) > float(team_a_score):
                    winner = team_b["roster_id"]
                    loser = team_a["roster_id"]
                else:
                    winner = "TIE"
                    loser = "TIE"
                pair = frozenset([team_a["roster_id"], team_b["roster_id"]])
                if (int(season) >= 2021 and int(week) < 15) or (
                    int(season) < 2021 and int(week) < 14
                ):
                    playoff_tier_type = "NONE"
                else:
                    bracket_entry = bracket.get(pair)
                    playoff_tier_type = (
                        bracket_entry["tier"] if bracket_entry else "LOSERS_BRACKET"
                    )
                team_a_starters_stats, team_a_starter_ids = (
                    compile_sleeper_starter_stats(
                        starters=team_a.get("starters", []),
                        starters_points=team_a.get("starters_points", []),
                        player_metadata=player_metadata,
                    )
                )
                team_b_starters_stats, team_b_starter_ids = (
                    compile_sleeper_starter_stats(
                        starters=team_b.get("starters", []),
                        starters_points=team_b.get("starters_points", []),
                        player_metadata=player_metadata,
                    )
                )
                team_a_bench_stats = compile_sleeper_bench_stats(
                    players=team_a.get("players", []),
                    players_points=team_a.get("players_points", {}),
                    starter_ids=team_a_starter_ids,
                    player_metadata=player_metadata,
                )
                team_b_bench_stats = compile_sleeper_bench_stats(
                    players=team_b.get("players", []),
                    players_points=team_b.get("players_points", {}),
                    starter_ids=team_b_starter_ids,
                    player_metadata=player_metadata,
                )
                all_matchups.append(
                    {
                        "team_a_roster_id": team_a["roster_id"],
                        "team_a_points": team_a_score,
                        "team_a_starters": team_a_starters_stats,
                        "team_a_bench": team_a_bench_stats,
                        "team_b_roster_id": team_b["roster_id"],
                        "team_b_points": team_b_score,
                        "team_b_starters": team_b_starters_stats,
                        "team_b_bench": team_b_bench_stats,
                        "playoff_tier_type": playoff_tier_type,
                        "winner": winner,
                        "loser": loser,
                        "team_a_week": week,
                        "team_a_season": item["season"],
                    }
                )

    return {
        "users": all_users,
        "rosters": all_rosters,
        "matchups": all_matchups,
        "brackets": all_brackets,
    }


def register_raw_data(
    raw_data: list[dict],
    con: duckdb.DuckDBPyConnection,
    platform: str,
    player_metadata: dict | None = None,
) -> None:
    """
    Register raw API response data as DuckDB views, grouped by data_type.

    Each view is named after its data_type (e.g. 'members', 'teams')
    and contains all seasons for that type.

    Args:
        raw_data: List of dicts with keys: season, data_type, data.
        con: A DuckDB connection object.
        platform: The fantasy platform the data originates from (e.g. 'ESPN', 'SLEEPER').
        player_metadata: Sleeper player ID → metadata mapping; only used when platform is SLEEPER.
    """
    if platform == "ESPN":
        grouped = _register_espn_raw_data(raw_data)
    else:
        grouped = _register_sleeper_raw_data(
            raw_data, player_metadata=player_metadata or {}
        )

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
    """
    Yield successive non-overlapping chunks of length `size` from `iterable`.

    Args:
        iterable: Any iterable to split.
        size: Maximum number of elements per chunk.

    Yields:
        Lists of up to `size` elements.
    """
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

    player_metadata: dict = {}
    if platform == "SLEEPER":
        try:
            player_metadata = read_s3_object(
                bucket=bucket, key="player-metadata/sleeper_nfl_players.json"
            )
            logger.info(
                "Loaded Sleeper player metadata (%d players)", len(player_metadata)
            )
        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] in ("NoSuchKey", "404"):
                logger.warning(
                    "Sleeper player metadata not found in S3; player names/positions will be null"
                )
            else:
                raise

    con = duckdb.connect()
    register_raw_data(
        raw_data=raw_data, con=con, platform=platform, player_metadata=player_metadata
    )

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

    PLAYOFF_BRACKET_SCHEMA = KeySchema(
        pk=f"LEAGUE#{canonical_league_id}",
        sk=lambda row: f"PLAYOFF_BRACKET#{row['season']}",
        entity_type=EntityType.PLAYOFF_BRACKET,
    )

    schemas = [TEAMS_SCHEMA, MATCHUPS_SCHEMA, STANDINGS_SCHEMA, PLAYOFF_BRACKET_SCHEMA]

    for schema in schemas:
        logger.info(f"Converting {schema.entity_type} data to DynamoDB items.")
        if schema in [TEAMS_SCHEMA, MATCHUPS_SCHEMA, PLAYOFF_BRACKET_SCHEMA]:
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

    standings_by_season: dict[str, list[dict]] = {  # noqa: F841
        str(season): group.to_dict("records")
        for season, group in standings_df.groupby("season")
    }
    matchups_by_season: dict[str, list[dict]] = {  # noqa: F841
        str(season): group.to_dict("records")
        for season, group in matchups_df.groupby("season")
    }

    write_metadata_items(
        league_id=canonical_league_id, refresh=previous_version_id is not None
    )

    # TODO: uncomment after deploying app to avoid wasted API costs
    # all_raw_data: list[dict[str, Any]] = list(raw_data)  # noqa: ERA001
    # additional_seasons = [s for s in all_seasons if s not in set(seasons_to_process)]  # noqa: ERA001
    # if additional_seasons:  # noqa: ERA001
    #     logger.info(  # noqa: ERA001
    #         "Loading additional seasons for manager recap: %s", additional_seasons  # noqa: ERA001
    #     )  # noqa: ERA001
    #     with ThreadPoolExecutor(max_workers=10) as executor:  # noqa: ERA001
    #         future_to_season = {  # noqa: ERA001
    #             executor.submit(read_s3_object, bucket, f"{prefix}/{s}.json"): s  # noqa: ERA001
    #             for s in additional_seasons  # noqa: ERA001
    #         }  # noqa: ERA001
    #         for future in as_completed(future_to_season):  # noqa: ERA001
    #             season = future_to_season[future]  # noqa: ERA001
    #             try:  # noqa: ERA001
    #                 all_raw_data.extend(future.result())  # noqa: ERA001
    #             except Exception as exc:  # noqa: ERA001
    #                 logger.error("Failed to load season %s for recap: %s", season, exc)  # noqa: ERA001
    # con_recap = duckdb.connect()  # noqa: ERA001
    # register_raw_data(raw_data=all_raw_data, con=con_recap, platform=platform)  # noqa: ERA001
    # recap_teams_rel = con_recap.sql(QUERIES["TEAMS"][platform])  # noqa: ERA001
    # con_recap.register("teams_output", recap_teams_rel)  # noqa: ERA001
    # recap_matchups_rel = con_recap.sql(QUERIES["MATCHUPS"][platform])  # noqa: ERA001
    # con_recap.register("matchups_output", recap_matchups_rel)  # noqa: ERA001
    # all_standings_rows = con_recap.sql(QUERIES["STANDINGS"]).df().to_dict("records")  # noqa: ERA001
    # all_matchups_rows = recap_matchups_rel.df().to_dict("records")  # noqa: ERA001
    # try:  # noqa: ERA001
    #     asyncio.run(  # noqa: ERA001
    #         generate_recaps_for_all_seasons(  # noqa: ERA001
    #             table=table,  # noqa: ERA001
    #             api_key=os.environ["ANTHROPIC_API_KEY"],  # noqa: ERA001
    #             pk=f"LEAGUE#{canonical_league_id}",  # noqa: ERA001
    #             seasons=seasons_to_process,  # noqa: ERA001
    #             standings_by_season=standings_by_season,  # noqa: ERA001
    #             matchups_by_season=matchups_by_season,  # noqa: ERA001
    #         )  # noqa: ERA001
    #     )  # noqa: ERA001
    # except Exception as e:  # noqa: ERA001
    #     logger.error("Season AI recap generation failed: %s", e)  # noqa: ERA001
    # try:  # noqa: ERA001
    #     asyncio.run(  # noqa: ERA001
    #         generate_manager_recaps(  # noqa: ERA001
    #             table=table,  # noqa: ERA001
    #             api_key=os.environ["ANTHROPIC_API_KEY"],  # noqa: ERA001
    #             pk=f"LEAGUE#{canonical_league_id}",  # noqa: ERA001
    #             all_standings_rows=all_standings_rows,  # noqa: ERA001
    #             all_matchups_rows=all_matchups_rows,  # noqa: ERA001
    #         )  # noqa: ERA001
    #     )  # noqa: ERA001
    # except Exception as e:  # noqa: ERA001
    #     logger.error("Manager AI recap generation failed: %s", e)  # noqa: ERA001
