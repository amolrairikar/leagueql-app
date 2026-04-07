from typing import Any

import duckdb
import pandas as pd

from queries import ESPN_QUERIES, SLEEPER_QUERIES


class Transformer:
    """
    Class for transforming raw API response data into format consumed by application.

    Attributes:
        platform: The platform the league is on (e.g., ESPN, SLEEPER)

    Methods:
        __init__(platform): Constructor.
        transform(raw_data): Orchestrates the data transformation process.
        _prepare_table_data_espn(raw_data): Loads raw ESPN data into entity-data mapping with season added to data.
        _prepare_table_data_sleeper(raw_data): Loads raw SLEEPER data into entity-data mapping with season added to data.
        _load_data_duckdb(table_data): Loads each entity into DuckDB as a table.
        _execute_transformations(con): Executes SQL transformations from query config file and assigns sort key.
    """

    def __init__(self, platform: str):
        """Constructor."""
        self.platform = platform

    def transform(self, raw_data: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Orchestrates the data transformation process.

        Args:
            raw_data: The raw API response data to process.

        Returns:
            The processed data organized in key-value pairs of DynamoDB sort key and processed data.
        """
        if self.platform == "ESPN":
            data = self._prepare_table_data_espn(raw_data=raw_data)
        elif self.platform == "SLEEPER":
            data = self._prepare_table_data_sleeper(raw_data=raw_data)
        else:
            raise ValueError("Invalid platform. Please specify one of ESPN or SLEEPER.")
        return self._execute_transformations(con=self._load_data_duckdb(data=data))

    def _prepare_table_data_espn(
        self, raw_data: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Loads raw ESPN data into entity-data mapping with season added to data
        and any initial data processing performed.

        Args:
            raw_data: List of dictionaries containing raw API response data.

        Returns:
            Mapping of entity (DuckDB table name) to raw data.
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
            if item["data_type"].startswith("matchups"):
                for record in item["data"].get("matchups", []):
                    team_a_id = record.get("home", {}).get("teamId", "")
                    team_a_score = record.get("home", {}).get("totalPoints", "0.00")
                    team_b_id = record.get("away", {}).get("teamId", "")
                    team_b_score = record.get("away", {}).get("totalPoints", "0.00")
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
                        "winner": winner,
                        "loser": loser,
                        "week": week,
                        "season": item["season"],
                    }
                    all_matchups.append(cleaned_matchup)

        return {
            "members": all_members,
            "teams": all_teams,
            "matchups": all_matchups,
        }

    def _prepare_table_data_sleeper(
        self, raw_data: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Loads raw SLEEPER data into entity-data mapping with season added to data.

        Args:
            raw_data: List of dictionaries containing raw API response data.

        Returns:
            Mapping of entity (DuckDB table name) to raw data.
        """
        all_teams = []

        for item in raw_data:
            if item["data_type"] == "users":
                for record in item["data"]:
                    record_copy = record.copy()
                    record_copy["season"] = item["season"]
                    all_teams.append(record_copy)

        return {
            "teams": all_teams,
        }

    def _load_data_duckdb(self, data: dict[str, Any]) -> duckdb.DuckDBPyConnection:
        """
        Loads each entity into DuckDB as a table.

        Args:
            data: Mapping of entity (table name) to raw data to load into DuckDB.

        Returns:
            DuckDB connection with all source tables loaded in.
        """
        con = duckdb.connect(database=":memory:")
        for table_name, records in data.items():
            df = pd.json_normalize(records)
            con.register("temp_df", df)
            con.execute(f"CREATE TABLE {table_name} AS SELECT * FROM temp_df")
        return con

    def _execute_transformations(
        self, con: duckdb.DuckDBPyConnection
    ) -> dict[str, Any]:
        """
        Executes SQL transformations from query config file and assigns sort key.

        Args:
            con: DuckDB connection with all source tables loaded in.

        Returns:
            Mapping of DynamoDB sort key to processed data.
        """
        sql_query_config = (
            ESPN_QUERIES if self.platform.lower() == "espn" else SLEEPER_QUERIES
        )
        results = {}
        for key, query in sql_query_config.items():
            # Results that are partitioned by season and/or week
            if key in ("MATCHUPS",):
                # Partition results by season and week, returning a mapping of sort key to data for each season-week combination
                res = con.execute(query)
                columns = [desc[0] for desc in res.description]
                rows = res.fetchall()
                data = [dict(zip(columns, row)) for row in rows]
                for record in data:
                    season = record["season"]
                    week = record["week"]
                    sort_key = f"{key}#{season}#{week}"
                    if sort_key not in results:
                        results[sort_key] = []
                    results[sort_key].append(record)
            # Results that are not partitioned by season and/or week
            else:
                res = con.execute(query)
                columns = [desc[0] for desc in res.description]
                rows = res.fetchall()
                data = [dict(zip(columns, row)) for row in rows]
                results[key] = data
        return results
