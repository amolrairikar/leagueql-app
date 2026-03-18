import os
import yaml
from typing import Any

import duckdb
import pandas as pd


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

    def transform(self, raw_data) -> dict[str, Any]:
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
        Loads raw ESPN data into entity-data mapping with season added to data.

        Args:
            raw_data: List of dictionaries containing raw API response data.

        Returns:
            Mapping of entity (DuckDB table name) to raw data.
        """
        all_members, all_teams = [], []

        for item in raw_data:
            if item["data_type"] == "league_information":
                for record in item["data"].get("members", []):
                    record["season"] = item["season"]
                    all_members.append(record)
                for record in item["data"].get("teams", []):
                    record["season"] = item["season"]
                    all_teams.append(record)

        return {
            "members": all_members,
            "teams": all_teams,
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
                    record["season"] = item["season"]
                    all_teams.append(record)

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
        base_path = os.path.dirname(__file__)
        yaml_path = os.path.join(base_path, "transformation_queries.yaml")
        with open(yaml_path) as stream:
            sql_query_config = yaml.safe_load(stream=stream)[self.platform.lower()]
        results = {}
        for query in sql_query_config:
            # Results that are partitioned by season and/or week
            if sql_query_config[query]["database_key"] in (
                "MATCHUPS"
            ):  # TODO: Fill out later
                pass
            # Results that are not partitioned by season and/or week
            else:
                res = con.execute(sql_query_config[query]["query"])
                columns = [desc[0] for desc in res.description]
                rows = res.fetchall()
                data = [dict(zip(columns, row)) for row in rows]
                results[sql_query_config[query]["database_key"]] = data
        return results
