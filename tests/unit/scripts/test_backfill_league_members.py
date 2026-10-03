"""Tests for scripts/utility_scripts/backfill_league_members.py (backend/user-leagues)."""

import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import botocore.exceptions
import pytest

_SCRIPT = (
    Path(__file__).parents[3]
    / "scripts"
    / "utility_scripts"
    / "backfill_league_members.py"
)


@pytest.fixture(scope="module")
def script():
    spec = importlib.util.spec_from_file_location("backfill_league_members", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["backfill_league_members"] = mod
    spec.loader.exec_module(mod)
    yield mod
    sys.modules.pop("backfill_league_members", None)


# canon-1: owner + one invited member. canon-2: owner only (on the second GSI3 page).
# canon-3: system onboard (no owner, no members).
_FULL_METADATA = {
    "LEAGUE#canon-1": {"owner_user_id": "owner_a", "members": {"owner_a", "mate"}},
    "LEAGUE#canon-2": {"owner_user_id": "owner_b", "members": {"owner_b"}},
    "LEAGUE#canon-3": {},
}


def _table():
    table = MagicMock()
    table.query.side_effect = [
        {
            "Items": [
                {"PK": "LEAGUE#canon-1", "onboarded_at": "2024-01-01T00:00:00Z"},
                {"PK": "LEAGUE#canon-3", "onboarded_at": "2024-02-01T00:00:00Z"},
            ],
            "LastEvaluatedKey": {"page": 2},
        },
        {"Items": [{"PK": "LEAGUE#canon-2", "onboarded_at": "2025-01-01T00:00:00Z"}]},
    ]
    table.get_item.side_effect = lambda Key, **_: {"Item": _FULL_METADATA[Key["PK"]]}
    return table


def _puts(table):
    return {
        (c.kwargs["Item"]["PK"], c.kwargs["Item"]["SK"], c.kwargs["Item"]["joined_at"])
        for c in table.put_item.call_args_list
    }


class TestBackfill:
    def test_dry_run_counts_without_writing(self, script):
        table = _table()
        counts = script.backfill(table, execute=False)
        assert counts == {"leagues": 3, "created": 3, "skipped": 0}
        table.put_item.assert_not_called()

    def test_execute_indexes_owner_and_members_with_onboard_time(self, script):
        table = _table()
        counts = script.backfill(table, execute=True)
        assert counts == {"leagues": 3, "created": 3, "skipped": 0}
        assert _puts(table) == {
            ("LEAGUE#canon-1", "MEMBER#owner_a", "2024-01-01T00:00:00Z"),
            ("LEAGUE#canon-1", "MEMBER#mate", "2024-01-01T00:00:00Z"),
            ("LEAGUE#canon-2", "MEMBER#owner_b", "2025-01-01T00:00:00Z"),
        }
        # Paginated through GSI3.
        assert table.query.call_args_list[1].kwargs["ExclusiveStartKey"] == {"page": 2}
        assert table.query.call_args_list[0].kwargs["IndexName"] == "GSI3"

    def test_rerun_is_idempotent(self, script):
        table = _table()
        table.put_item.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "ConditionalCheckFailedException"}}, "PutItem"
        )
        counts = script.backfill(table, execute=True)
        assert counts == {"leagues": 3, "created": 0, "skipped": 3}
        # Every put is conditional, so existing joined_at values are never overwritten.
        assert all(
            c.kwargs["ConditionExpression"] == "attribute_not_exists(PK)"
            for c in table.put_item.call_args_list
        )

    def test_missing_metadata_item_indexes_no_one(self, script):
        table = MagicMock()
        table.query.return_value = {"Items": [{"PK": "LEAGUE#gone"}]}
        table.get_item.return_value = {}
        assert script.backfill(table, execute=True) == {
            "leagues": 1,
            "created": 0,
            "skipped": 0,
        }


class TestCli:
    @pytest.mark.parametrize(
        ("argv", "expected"),
        [
            ([], "leagueql-table-dev"),
            (["--environment", "prod"], "leagueql-table-prod"),
            (["--table", "custom"], "custom"),
        ],
    )
    def test_resolve_table(self, script, argv, expected):
        assert script.resolve_table(script.parse_args(argv)) == expected

    @pytest.mark.parametrize("execute", [False, True])
    def test_main_runs_backfill(self, script, execute):
        resource = MagicMock()
        argv = ["--environment", "prod"] + (["--execute"] if execute else [])
        with (
            patch.object(script.boto3, "resource", return_value=resource),
            patch.object(
                script,
                "backfill",
                return_value={"leagues": 1, "created": 1, "skipped": 0},
            ) as run,
        ):
            assert script.main(argv) == {"leagues": 1, "created": 1, "skipped": 0}
        resource.Table.assert_called_once_with("leagueql-table-prod")
        run.assert_called_once_with(resource.Table.return_value, execute)
