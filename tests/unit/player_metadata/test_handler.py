"""Tests for player_metadata/handler.py."""

import json
from unittest.mock import MagicMock, patch

import pytest


class TestFetchNflState:
    def test_returns_state_on_success(self, player_metadata_handler):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"season_type": "regular", "season": "2024"}
        mock_resp.raise_for_status = MagicMock()
        mock_session = MagicMock()
        mock_session.get.return_value = mock_resp

        with patch.object(player_metadata_handler, "http_session", mock_session):
            result = player_metadata_handler.fetch_nfl_state()
        assert result == {"season_type": "regular", "season": "2024"}

    def test_returns_none_on_exception(self, player_metadata_handler):
        mock_session = MagicMock()
        mock_session.get.side_effect = Exception("timeout")

        with patch.object(player_metadata_handler, "http_session", mock_session):
            result = player_metadata_handler.fetch_nfl_state()
        assert result is None


class TestLambdaHandlerPlayerMetadata:
    def _make_valid_players(self) -> dict:
        return {
            "1": {
                "first_name": "Joe",
                "last_name": "Burrow",
                "position": "QB",
                "status": "Active",
            },
            "2": {
                "first_name": "Ja",
                "last_name": "Marr Chase",
                "position": "WR",
                "status": "Active",
            },
        }

    def test_skips_when_off_season(self, player_metadata_handler):
        with (
            patch.object(
                player_metadata_handler,
                "fetch_nfl_state",
                return_value={"season_type": "off"},
            ),
        ):
            player_metadata_handler.lambda_handler({}, MagicMock())
            # No fetch should happen

    def test_fetches_and_uploads_player_metadata(self, player_metadata_handler):
        players = self._make_valid_players()
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = players
        mock_session = MagicMock()
        mock_session.get.return_value = mock_resp

        mock_s3 = MagicMock()

        with (
            patch.object(
                player_metadata_handler,
                "fetch_nfl_state",
                return_value={"season_type": "regular"},
            ),
            patch.object(player_metadata_handler, "http_session", mock_session),
            patch.object(player_metadata_handler, "s3_client", mock_s3),
        ):
            player_metadata_handler.lambda_handler({}, MagicMock())

        mock_s3.put_object.assert_called_once()
        call_kwargs = mock_s3.put_object.call_args[1]
        assert call_kwargs["Key"] == "player-metadata/sleeper_nfl_players.json"
        written = json.loads(call_kwargs["Body"])
        assert "1" in written

    def test_raises_on_empty_response(self, player_metadata_handler):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {}
        mock_session = MagicMock()
        mock_session.get.return_value = mock_resp

        with (
            patch.object(
                player_metadata_handler,
                "fetch_nfl_state",
                return_value={"season_type": "regular"},
            ),
            patch.object(player_metadata_handler, "http_session", mock_session),
        ):
            with pytest.raises(ValueError, match="Unexpected player metadata"):
                player_metadata_handler.lambda_handler({}, MagicMock())

    def test_raises_on_non_dict_response(self, player_metadata_handler):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = [1, 2, 3]
        mock_session = MagicMock()
        mock_session.get.return_value = mock_resp

        with (
            patch.object(
                player_metadata_handler,
                "fetch_nfl_state",
                return_value={"season_type": "regular"},
            ),
            patch.object(player_metadata_handler, "http_session", mock_session),
        ):
            with pytest.raises(ValueError):
                player_metadata_handler.lambda_handler({}, MagicMock())

    def test_raises_when_required_fields_missing(self, player_metadata_handler):
        players = {str(i): {"first_name": f"Player{i}"} for i in range(15)}
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = players
        mock_session = MagicMock()
        mock_session.get.return_value = mock_resp

        with (
            patch.object(
                player_metadata_handler,
                "fetch_nfl_state",
                return_value={"season_type": "regular"},
            ),
            patch.object(player_metadata_handler, "http_session", mock_session),
        ):
            with pytest.raises(ValueError, match="missing required fields"):
                player_metadata_handler.lambda_handler({}, MagicMock())

    def test_proceeds_when_nfl_state_is_none(self, player_metadata_handler):
        """When fetch_nfl_state returns None, assume season is active and proceed."""
        players = self._make_valid_players()
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = players
        mock_session = MagicMock()
        mock_session.get.return_value = mock_resp

        mock_s3 = MagicMock()

        with (
            patch.object(player_metadata_handler, "fetch_nfl_state", return_value=None),
            patch.object(player_metadata_handler, "http_session", mock_session),
            patch.object(player_metadata_handler, "s3_client", mock_s3),
        ):
            player_metadata_handler.lambda_handler({}, MagicMock())

        mock_s3.put_object.assert_called_once()
