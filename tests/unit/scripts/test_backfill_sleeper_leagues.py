"""Tests for the single-league resolver in backfill_sleeper_leagues.py."""

import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_SCRIPT = (
    Path(__file__).parents[3]
    / "scripts"
    / "utility_scripts"
    / "backfill_sleeper_leagues.py"
)


def _load_module(unique_name: str, path: Path) -> object:
    spec = importlib.util.spec_from_file_location(unique_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[unique_name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def backfill():
    mod = _load_module("backfill_sleeper_leagues", _SCRIPT)
    yield mod
    sys.modules.pop("backfill_sleeper_leagues", None)


def _lookup_item(canonical: str) -> dict:
    return {"Item": {"canonical_league_id": {"S": canonical}}}


def _gsi2_items() -> dict:
    # Two seasons of one canonical (chain head is the most-recent season, league 200)
    # plus a second, unrelated canonical.
    return {
        "Items": [
            {
                "canonical_league_id": {"S": "canon-1"},
                "league_id": {"S": "200"},
                "seasons": {"SS": ["2024"]},
            },
            {
                "canonical_league_id": {"S": "canon-1"},
                "league_id": {"S": "100"},
                "seasons": {"SS": ["2023"]},
            },
            {
                "canonical_league_id": {"S": "canon-2"},
                "league_id": {"S": "300"},
                "seasons": {"SS": ["2024"]},
            },
        ]
    }


def _make_client(*, lookup_response=None) -> MagicMock:
    client = MagicMock()
    client.query.return_value = _gsi2_items()
    if lookup_response is not None:
        client.get_item.return_value = lookup_response
    return client


class TestResolveSingleLeague:
    def test_canonical_id_skips_lookup_and_returns_head(self, backfill):
        client = _make_client()
        result = backfill.resolve_single_league(
            client, "tbl", canonical_league_id="canon-1"
        )
        assert result == [{"league_id": "200", "canonical_league_id": "canon-1"}]
        client.get_item.assert_not_called()

    def test_league_id_resolves_canonical_then_filters_to_head(self, backfill):
        # A non-head league ID (100) still resolves to the chain head (200).
        client = _make_client(lookup_response=_lookup_item("canon-1"))
        result = backfill.resolve_single_league(client, "tbl", league_id="100")
        assert result == [{"league_id": "200", "canonical_league_id": "canon-1"}]
        client.get_item.assert_called_once_with(
            TableName="tbl",
            Key={
                "PK": {"S": "LEAGUE#100#PLATFORM#SLEEPER"},
                "SK": {"S": "LEAGUE_LOOKUP"},
            },
        )

    def test_missing_lookup_item_returns_empty(self, backfill, caplog):
        client = _make_client(lookup_response={})  # no "Item"
        result = backfill.resolve_single_league(client, "tbl", league_id="999")
        assert result == []
        assert "No LEAGUE_LOOKUP" in caplog.text

    def test_canonical_not_among_leagues_returns_empty(self, backfill, caplog):
        client = _make_client()
        result = backfill.resolve_single_league(
            client, "tbl", canonical_league_id="canon-999"
        )
        assert result == []
        assert "not found among onboarded Sleeper leagues" in caplog.text
