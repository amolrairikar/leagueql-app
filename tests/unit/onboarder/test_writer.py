"""Tests for onboarder/writer.py."""

import json
from unittest.mock import MagicMock, patch

import botocore.exceptions
import pytest


class TestUploadResultsToS3:
    def test_uploads_per_season_files(self, mock_s3):
        from writer import upload_results_to_s3

        mock_s3.get_object.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "NoSuchKey", "Message": "Not found"}}, "GetObject"
        )
        results = [
            {"season": "2024", "data_type": "users", "data": []},
            {"season": "2023", "data_type": "users", "data": []},
        ]
        upload_results_to_s3(results, "my-bucket", "raw-api-data/abc", "SLEEPER")

        put_calls = mock_s3.put_object.call_args_list
        keys = [call[1]["Key"] for call in put_calls]
        assert "raw-api-data/abc/2024.json" in keys
        assert "raw-api-data/abc/2023.json" in keys
        assert "raw-api-data/abc/manifest.json" in keys

    def test_creates_new_manifest_when_none_exists(self, mock_s3):
        from writer import upload_results_to_s3

        mock_s3.get_object.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "NoSuchKey", "Message": "Not found"}}, "GetObject"
        )
        results = [{"season": "2024", "data_type": "users", "data": []}]
        upload_results_to_s3(results, "bucket", "prefix", "SLEEPER")

        manifest_call = next(
            c for c in mock_s3.put_object.call_args_list if "manifest" in c[1]["Key"]
        )
        manifest = json.loads(manifest_call[1]["Body"])
        assert "SLEEPER" in manifest
        assert "2024" in manifest["SLEEPER"]

    def test_merges_with_existing_manifest(self, mock_s3):
        from writer import upload_results_to_s3

        existing = {"SLEEPER": ["2022", "2023"]}
        mock_s3.get_object.return_value = {
            "Body": MagicMock(read=lambda: json.dumps(existing).encode())
        }
        results = [{"season": "2024", "data_type": "users", "data": []}]
        upload_results_to_s3(results, "bucket", "prefix", "SLEEPER")

        manifest_call = next(
            c for c in mock_s3.put_object.call_args_list if "manifest" in c[1]["Key"]
        )
        manifest = json.loads(manifest_call[1]["Body"])
        assert manifest["SLEEPER"] == ["2022", "2023", "2024"]

    def test_raises_on_unexpected_s3_error(self, mock_s3):
        from writer import upload_results_to_s3

        mock_s3.put_object.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Denied"}}, "PutObject"
        )
        with pytest.raises(botocore.exceptions.ClientError):
            upload_results_to_s3(
                [{"season": "2024", "data_type": "users", "data": []}],
                "bucket",
                "prefix",
                "SLEEPER",
            )

    def test_raises_on_non_nosuchkey_manifest_get_error(self, mock_s3):
        from writer import upload_results_to_s3

        mock_s3.get_object.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Denied"}}, "GetObject"
        )
        with pytest.raises(botocore.exceptions.ClientError):
            upload_results_to_s3(
                [{"season": "2024", "data_type": "users", "data": []}],
                "bucket",
                "prefix",
                "SLEEPER",
            )


class TestWriteOnboardingStatusToDynamodb:
    def test_onboard_creates_metadata_and_lookup(self, mock_dynamodb):
        from writer import write_onboarding_status_to_dynamodb

        write_onboarding_status_to_dynamodb(
            league_id="123",
            platform="SLEEPER",
            canonical_league_id="canon-abc",
            seasons=["2024"],
            request_type="ONBOARD",
        )
        call_args = mock_dynamodb.transact_write_items.call_args[1]
        items = call_args["TransactItems"]
        assert len(items) == 2
        ops = {list(item.keys())[0] for item in items}
        assert "Put" in ops

    def test_refresh_updates_metadata_and_lookup(self, mock_dynamodb):
        from writer import write_onboarding_status_to_dynamodb

        write_onboarding_status_to_dynamodb(
            league_id="123",
            platform="SLEEPER",
            canonical_league_id="canon-abc",
            seasons=["2024"],
            request_type="REFRESH",
        )
        call_args = mock_dynamodb.transact_write_items.call_args[1]
        items = call_args["TransactItems"]
        ops = {list(item.keys())[0] for item in items}
        assert "Update" in ops

    def test_refresh_new_season_uses_put_for_lookup(self, mock_dynamodb):
        from writer import write_onboarding_status_to_dynamodb

        write_onboarding_status_to_dynamodb(
            league_id="new-123",
            platform="SLEEPER",
            canonical_league_id="canon-abc",
            seasons=["2025"],
            request_type="REFRESH",
            is_new_season_refresh=True,
        )
        call_args = mock_dynamodb.transact_write_items.call_args[1]
        items = call_args["TransactItems"]
        ops = [list(item.keys())[0] for item in items]
        assert "Put" in ops

    def test_raises_on_missing_env_var(self, mock_dynamodb):
        from writer import write_onboarding_status_to_dynamodb
        import os

        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(KeyError):
                write_onboarding_status_to_dynamodb(
                    league_id="123",
                    platform="SLEEPER",
                    canonical_league_id="canon-abc",
                    seasons=["2024"],
                    request_type="ONBOARD",
                )

    def test_raises_on_client_error(self, mock_dynamodb):
        from writer import write_onboarding_status_to_dynamodb

        mock_dynamodb.transact_write_items.side_effect = (
            botocore.exceptions.ClientError(
                {"Error": {"Code": "InternalError", "Message": "fail"}},
                "TransactWriteItems",
            )
        )
        with pytest.raises(botocore.exceptions.ClientError):
            write_onboarding_status_to_dynamodb(
                league_id="123",
                platform="SLEEPER",
                canonical_league_id="canon-abc",
                seasons=["2024"],
                request_type="ONBOARD",
            )
