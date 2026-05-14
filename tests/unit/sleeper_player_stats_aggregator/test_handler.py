"""Tests for sleeper_player_stats_aggregator/handler.py."""

import json
from unittest.mock import MagicMock, patch


class TestReadStagingFile:
    def test_reads_and_parses_json(self):
        import handler

        mock_response = {
            "Body": MagicMock(
                read=lambda: json.dumps(
                    {"player-1": {"2024": {"rush_yd": 100}}}
                ).encode()
            )
        }

        with patch.object(handler, "s3_client") as mock_s3:
            mock_s3.get_object.return_value = mock_response
            result = handler.read_staging_file("my-bucket", "staging/abc.json")

        assert result == {"player-1": {"2024": {"rush_yd": 100}}}
        mock_s3.get_object.assert_called_once_with(
            Bucket="my-bucket", Key="staging/abc.json"
        )


class TestLambdaHandler:
    def test_merges_staging_files_and_writes_final(self, mock_context):
        import handler

        staging_files = [
            {"player-1": {"2024": {"rush_yd": 100}}},
            {"player-2": {"2024": {"rec_yd": 80}}},
        ]

        def mock_paginate(*_, **__):
            return iter(
                [
                    {
                        "Contents": [
                            {"Key": "player-stats/staging/file1.json"},
                            {"Key": "player-stats/staging/file2.json"},
                        ]
                    }
                ]
            )

        with patch.object(handler, "s3_client") as mock_s3:
            mock_paginator = MagicMock()
            mock_paginator.paginate.side_effect = mock_paginate
            mock_s3.get_paginator.return_value = mock_paginator
            mock_s3.get_object.side_effect = [
                {"Body": MagicMock(read=lambda d=d: json.dumps(d).encode())}
                for d in staging_files
            ]
            handler.lambda_handler({}, mock_context)

        put_call = mock_s3.put_object.call_args
        assert put_call[1]["Key"] == "player-stats/sleeper_nfl_player_stats.json"
        merged = json.loads(put_call[1]["Body"])
        assert "player-1" in merged
        assert "player-2" in merged

    def test_no_op_when_no_staging_files(self, mock_context):
        import handler

        def mock_paginate(*_, **__):
            return iter([{"Contents": []}])

        with patch.object(handler, "s3_client") as mock_s3:
            mock_paginator = MagicMock()
            mock_paginator.paginate.side_effect = mock_paginate
            mock_s3.get_paginator.return_value = mock_paginator
            handler.lambda_handler({}, mock_context)

        mock_s3.put_object.assert_not_called()

    def test_skips_complete_json_when_listing(self, mock_context):
        import handler

        def mock_paginate(*_, **__):
            return iter(
                [
                    {
                        "Contents": [
                            {"Key": "player-stats/staging/complete.json"},
                        ]
                    }
                ]
            )

        with patch.object(handler, "s3_client") as mock_s3:
            mock_paginator = MagicMock()
            mock_paginator.paginate.side_effect = mock_paginate
            mock_s3.get_paginator.return_value = mock_paginator
            handler.lambda_handler({}, mock_context)

        mock_s3.put_object.assert_not_called()

    def test_deletes_all_staging_files_including_complete(self, mock_context):
        import handler

        staging_keys = [
            {"Key": "player-stats/staging/f1.json"},
            {"Key": "player-stats/staging/complete.json"},
        ]

        def mock_paginate(*_, **__):
            return iter([{"Contents": staging_keys}])

        with patch.object(handler, "s3_client") as mock_s3:
            mock_paginator = MagicMock()
            mock_paginator.paginate.side_effect = mock_paginate
            mock_s3.get_paginator.return_value = mock_paginator
            mock_s3.get_object.return_value = {
                "Body": MagicMock(
                    read=lambda: json.dumps({"p1": {"2024": {"rush_yd": 10}}}).encode()
                )
            }
            handler.lambda_handler({}, mock_context)

        delete_call = mock_s3.delete_objects.call_args
        deleted_keys = {obj["Key"] for obj in delete_call[1]["Delete"]["Objects"]}
        assert "player-stats/staging/f1.json" in deleted_keys
        assert "player-stats/staging/complete.json" in deleted_keys

    def test_merges_seasons_for_same_player(self, mock_context):
        import handler

        staging_files = [
            {"player-1": {"2023": {"rush_yd": 80}}},
            {"player-1": {"2024": {"rush_yd": 120}}},
        ]

        def mock_paginate(*_, **__):
            return iter(
                [
                    {
                        "Contents": [
                            {"Key": "player-stats/staging/f1.json"},
                            {"Key": "player-stats/staging/f2.json"},
                        ]
                    }
                ]
            )

        with patch.object(handler, "s3_client") as mock_s3:
            mock_paginator = MagicMock()
            mock_paginator.paginate.side_effect = mock_paginate
            mock_s3.get_paginator.return_value = mock_paginator
            mock_s3.get_object.side_effect = [
                {"Body": MagicMock(read=lambda d=d: json.dumps(d).encode())}
                for d in staging_files
            ]
            handler.lambda_handler({}, mock_context)

        merged = json.loads(mock_s3.put_object.call_args[1]["Body"])
        assert "2023" in merged["player-1"]
        assert "2024" in merged["player-1"]
