"""Tests for player_metadata/handler.py."""

import json
from unittest.mock import MagicMock, patch

import pytest


class TestFetchNflState:
    def test_returns_dict_on_success(self):
        import handler

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"season_type": "regular", "week": 5}

        with patch.object(handler, "http_session") as mock_session:
            mock_session.get.return_value = mock_response
            result = handler.fetch_nfl_state()

        assert result == {"season_type": "regular", "week": 5}

    def test_returns_none_on_exception(self):
        import handler

        with patch.object(handler, "http_session") as mock_session:
            mock_session.get.side_effect = Exception("network error")
            result = handler.fetch_nfl_state()

        assert result is None


class TestLambdaHandler:
    def test_skips_when_nfl_season_is_off(self, mock_context):
        import handler

        with patch.object(handler, "fetch_nfl_state") as mock_state:
            mock_state.return_value = {"season_type": "off"}
            result = handler.lambda_handler({}, mock_context)

        assert result is None

    def test_raises_on_non_dict_response(self, mock_context):
        import handler

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = []

        with (
            patch.object(handler, "fetch_nfl_state", return_value=None),
            patch.object(handler, "http_session") as mock_session,
        ):
            mock_session.get.return_value = mock_response
            with pytest.raises(ValueError, match="Unexpected player metadata response"):
                handler.lambda_handler({}, mock_context)

    def test_raises_on_missing_required_fields(self, mock_context):
        import handler

        players = {
            str(i): {"first_name": "Player", "last_name": str(i)} for i in range(15)
        }
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = players

        with (
            patch.object(handler, "fetch_nfl_state", return_value=None),
            patch.object(handler, "http_session") as mock_session,
        ):
            mock_session.get.return_value = mock_response
            with pytest.raises(ValueError, match="missing required fields"):
                handler.lambda_handler({}, mock_context)

    def test_success_uploads_to_s3(self, mock_context):
        import handler

        players = {
            str(i): {"first_name": "F", "last_name": "L", "position": "QB"}
            for i in range(15)
        }
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = players

        with (
            patch.object(handler, "fetch_nfl_state", return_value=None),
            patch.object(handler, "http_session") as mock_session,
            patch.object(handler, "s3_client") as mock_s3,
        ):
            mock_session.get.return_value = mock_response
            handler.lambda_handler({}, mock_context)

        mock_s3.put_object.assert_called_once()
        call_kwargs = mock_s3.put_object.call_args[1]
        assert call_kwargs["Key"] == "player-metadata/sleeper_nfl_players.json"
        uploaded = json.loads(call_kwargs["Body"])
        assert len(uploaded) == 15
