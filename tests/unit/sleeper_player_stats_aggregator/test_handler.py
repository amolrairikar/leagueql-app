"""Tests for sleeper_player_stats_aggregator/handler.py."""

import json
from unittest.mock import MagicMock, patch


class TestLambdaHandlerStatsAggregator:
    def _make_s3_mock(self, staging_keys: list[str], staging_data: dict) -> MagicMock:
        mock_s3 = MagicMock()
        all_pages = [{"Contents": [{"Key": k} for k in staging_keys]}]

        def paginate_side_effect(*args, **kwargs):
            return all_pages

        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = all_pages
        mock_s3.get_paginator.return_value = mock_paginator

        def get_object_side_effect(Bucket, Key):
            data = staging_data.get(Key, {})
            body = MagicMock()
            body.read.return_value = json.dumps(data).encode()
            return {"Body": body}

        mock_s3.get_object.side_effect = get_object_side_effect
        return mock_s3

    def test_no_staging_files_is_noop(self, stats_aggregator_handler):
        mock_s3 = MagicMock()
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [{"Contents": []}]
        mock_s3.get_paginator.return_value = mock_paginator

        with patch.object(stats_aggregator_handler, "s3_client", mock_s3):
            stats_aggregator_handler.lambda_handler({}, MagicMock())

        mock_s3.put_object.assert_not_called()

    def test_merges_staging_files_and_writes_final(self, stats_aggregator_handler):
        staging_keys = [
            "player-stats/staging/msg-1.json",
            "player-stats/staging/msg-2.json",
            "player-stats/staging/complete.json",  # should be excluded
        ]
        staging_data = {
            "player-stats/staging/msg-1.json": {"p1": {"2024": {"pass_yd": 300}}},
            "player-stats/staging/msg-2.json": {"p2": {"2024": {"rush_yd": 100}}},
        }
        mock_s3 = self._make_s3_mock(staging_keys, staging_data)

        with patch.object(stats_aggregator_handler, "s3_client", mock_s3):
            stats_aggregator_handler.lambda_handler({}, MagicMock())

        put_call_keys = [c[1]["Key"] for c in mock_s3.put_object.call_args_list]
        assert "player-stats/sleeper_nfl_player_stats.json" in put_call_keys

        merged_body = next(
            c[1]["Body"]
            for c in mock_s3.put_object.call_args_list
            if c[1]["Key"] == "player-stats/sleeper_nfl_player_stats.json"
        )
        merged = json.loads(merged_body)
        assert "p1" in merged
        assert "p2" in merged

    def test_deletes_all_staging_files_after_merge(self, stats_aggregator_handler):
        staging_keys = [
            "player-stats/staging/msg-1.json",
            "player-stats/staging/complete.json",
        ]
        staging_data = {
            "player-stats/staging/msg-1.json": {"p1": {"2024": {"pass_yd": 100}}},
        }
        mock_s3 = self._make_s3_mock(staging_keys, staging_data)

        with patch.object(stats_aggregator_handler, "s3_client", mock_s3):
            stats_aggregator_handler.lambda_handler({}, MagicMock())

        mock_s3.delete_objects.assert_called_once()
        delete_call = mock_s3.delete_objects.call_args[1]["Delete"]["Objects"]
        deleted_keys = [o["Key"] for o in delete_call]
        assert "player-stats/staging/msg-1.json" in deleted_keys
        assert "player-stats/staging/complete.json" in deleted_keys

    def test_skips_none_stats_during_merge(self, stats_aggregator_handler):
        staging_keys = ["player-stats/staging/msg-1.json"]
        staging_data = {
            "player-stats/staging/msg-1.json": {
                "p1": {"2024": None, "2023": {"pass_yd": 200}}
            },
        }
        mock_s3 = self._make_s3_mock(staging_keys, staging_data)

        with patch.object(stats_aggregator_handler, "s3_client", mock_s3):
            stats_aggregator_handler.lambda_handler({}, MagicMock())

        put_body_str = next(
            c[1]["Body"]
            for c in mock_s3.put_object.call_args_list
            if c[1]["Key"] == "player-stats/sleeper_nfl_player_stats.json"
        )
        merged = json.loads(put_body_str)
        assert "2024" not in merged.get("p1", {})
        assert "2023" in merged["p1"]

    def test_merges_same_player_across_multiple_files(self, stats_aggregator_handler):
        staging_keys = [
            "player-stats/staging/msg-1.json",
            "player-stats/staging/msg-2.json",
        ]
        staging_data = {
            "player-stats/staging/msg-1.json": {"p1": {"2023": {"pass_yd": 200}}},
            "player-stats/staging/msg-2.json": {"p1": {"2024": {"pass_yd": 300}}},
        }
        mock_s3 = self._make_s3_mock(staging_keys, staging_data)

        with patch.object(stats_aggregator_handler, "s3_client", mock_s3):
            stats_aggregator_handler.lambda_handler({}, MagicMock())

        put_body_str = next(
            c[1]["Body"]
            for c in mock_s3.put_object.call_args_list
            if c[1]["Key"] == "player-stats/sleeper_nfl_player_stats.json"
        )
        merged = json.loads(put_body_str)
        assert "2023" in merged["p1"]
        assert "2024" in merged["p1"]
