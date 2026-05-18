"""Tests for onboarder/writer.py."""

import json
from unittest.mock import MagicMock, patch

import botocore.exceptions
import pytest


class TestUploadResultsToS3:
    def _make_results(self):
        return [
            {"season": "2024", "data_type": "users", "data": {"members": []}},
            {"season": "2024", "data_type": "rosters", "data": []},
            {"season": "2023", "data_type": "users", "data": {"members": []}},
        ]

    def test_uploads_per_season_json_and_manifest(self, onboarder_writer):
        mock_s3 = MagicMock()
        mock_s3.get_object.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "NoSuchKey"}}, "GetObject"
        )
        with patch.object(onboarder_writer, "_s3", mock_s3):
            onboarder_writer.upload_results_to_s3(
                results=self._make_results(),
                bucket_name="test-bucket",
                prefix="raw-api-data/league-abc",
                platform="SLEEPER",
            )
        put_keys = [c[1]["Key"] for c in mock_s3.put_object.call_args_list]
        assert any("2024.json" in k for k in put_keys)
        assert any("2023.json" in k for k in put_keys)
        assert any("manifest.json" in k for k in put_keys)

    def test_merges_existing_manifest(self, onboarder_writer):
        existing_manifest = {"SLEEPER": ["2022"]}
        mock_body = MagicMock()
        mock_body.read.return_value = json.dumps(existing_manifest).encode()
        mock_s3 = MagicMock()
        mock_s3.get_object.return_value = {"Body": mock_body}

        with patch.object(onboarder_writer, "_s3", mock_s3):
            onboarder_writer.upload_results_to_s3(
                results=self._make_results(),
                bucket_name="test-bucket",
                prefix="raw-api-data/league-abc",
                platform="SLEEPER",
            )

        manifest_call = next(
            c
            for c in mock_s3.put_object.call_args_list
            if "manifest.json" in c[1]["Key"]
        )
        written = json.loads(manifest_call[1]["Body"])
        assert "2022" in written["SLEEPER"]
        assert "2024" in written["SLEEPER"]

    def test_s3_client_error_non_nosuchkey_propagates(self, onboarder_writer):
        mock_s3 = MagicMock()
        mock_s3.put_object.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "denied"}}, "PutObject"
        )
        with patch.object(onboarder_writer, "_s3", mock_s3):
            with pytest.raises(botocore.exceptions.ClientError):
                onboarder_writer.upload_results_to_s3(
                    results=self._make_results(),
                    bucket_name="test-bucket",
                    prefix="raw-api-data/league-abc",
                    platform="SLEEPER",
                )

    def test_manifest_get_non_nosuchkey_error_propagates(self, onboarder_writer):
        mock_s3 = MagicMock()
        mock_s3.put_object = MagicMock()
        mock_s3.get_object.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "InternalError", "Message": "fail"}}, "GetObject"
        )
        with patch.object(onboarder_writer, "_s3", mock_s3):
            with pytest.raises(botocore.exceptions.ClientError):
                onboarder_writer.upload_results_to_s3(
                    results=self._make_results(),
                    bucket_name="test-bucket",
                    prefix="raw-api-data/league-abc",
                    platform="SLEEPER",
                )

    def test_nr_trace_headers_written_to_manifest_after_platform_key(
        self, onboarder_writer
    ):
        mock_s3 = MagicMock()
        mock_s3.get_object.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "NoSuchKey"}}, "GetObject"
        )
        with patch.object(onboarder_writer, "_s3", mock_s3):
            onboarder_writer.upload_results_to_s3(
                results=self._make_results(),
                bucket_name="test-bucket",
                prefix="raw-api-data/league-abc",
                platform="SLEEPER",
                nr_trace_headers={"traceparent": "00-abc-def-01"},
            )
        manifest_call = next(
            c
            for c in mock_s3.put_object.call_args_list
            if "manifest.json" in c[1]["Key"]
        )
        written = json.loads(manifest_call[1]["Body"])
        assert written["nr_trace"] == {"traceparent": "00-abc-def-01"}
        keys = list(written.keys())
        assert keys.index("SLEEPER") < keys.index("nr_trace")

    def test_no_nr_trace_headers_omits_nr_trace_from_manifest(self, onboarder_writer):
        mock_s3 = MagicMock()
        mock_s3.get_object.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "NoSuchKey"}}, "GetObject"
        )
        with patch.object(onboarder_writer, "_s3", mock_s3):
            onboarder_writer.upload_results_to_s3(
                results=self._make_results(),
                bucket_name="test-bucket",
                prefix="raw-api-data/league-abc",
                platform="SLEEPER",
            )
        manifest_call = next(
            c
            for c in mock_s3.put_object.call_args_list
            if "manifest.json" in c[1]["Key"]
        )
        written = json.loads(manifest_call[1]["Body"])
        assert "nr_trace" not in written


class TestWriteOnboardingStatusToDynamoDB:
    def test_onboard_writes_metadata_and_lookup(self, onboarder_writer, monkeypatch):
        monkeypatch.setenv("DYNAMODB_TABLE_NAME", "test-table")
        mock_ddb = MagicMock()
        with patch.object(onboarder_writer, "_dynamodb", mock_ddb):
            onboarder_writer.write_onboarding_status_to_dynamodb(
                league_id="123",
                platform="SLEEPER",
                canonical_league_id="canonical-abc",
                seasons=["2024"],
                request_type="ONBOARD",
            )
        mock_ddb.transact_write_items.assert_called_once()
        items = mock_ddb.transact_write_items.call_args[1]["TransactItems"]
        assert len(items) == 2

    def test_refresh_existing_season_uses_update(self, onboarder_writer, monkeypatch):
        monkeypatch.setenv("DYNAMODB_TABLE_NAME", "test-table")
        mock_ddb = MagicMock()
        with patch.object(onboarder_writer, "_dynamodb", mock_ddb):
            onboarder_writer.write_onboarding_status_to_dynamodb(
                league_id="123",
                platform="SLEEPER",
                canonical_league_id="canonical-abc",
                seasons=["2024"],
                request_type="REFRESH",
                is_new_season_refresh=False,
            )
        items = mock_ddb.transact_write_items.call_args[1]["TransactItems"]
        lookup_item = items[1]
        assert "Update" in lookup_item

    def test_refresh_new_season_uses_put(self, onboarder_writer, monkeypatch):
        monkeypatch.setenv("DYNAMODB_TABLE_NAME", "test-table")
        mock_ddb = MagicMock()
        with patch.object(onboarder_writer, "_dynamodb", mock_ddb):
            onboarder_writer.write_onboarding_status_to_dynamodb(
                league_id="456",
                platform="SLEEPER",
                canonical_league_id="canonical-abc",
                seasons=["2025"],
                request_type="REFRESH",
                is_new_season_refresh=True,
            )
        items = mock_ddb.transact_write_items.call_args[1]["TransactItems"]
        lookup_item = items[1]
        assert "Put" in lookup_item

    def test_missing_env_var_raises_key_error(self, onboarder_writer, monkeypatch):
        monkeypatch.delenv("DYNAMODB_TABLE_NAME", raising=False)
        with pytest.raises(KeyError):
            onboarder_writer.write_onboarding_status_to_dynamodb(
                league_id="123",
                platform="SLEEPER",
                canonical_league_id="canonical-abc",
                seasons=["2024"],
                request_type="ONBOARD",
            )

    def test_dynamodb_client_error_propagates(self, onboarder_writer, monkeypatch):
        monkeypatch.setenv("DYNAMODB_TABLE_NAME", "test-table")
        mock_ddb = MagicMock()
        mock_ddb.transact_write_items.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "InternalError", "Message": "fail"}},
            "TransactWriteItems",
        )
        with patch.object(onboarder_writer, "_dynamodb", mock_ddb):
            with pytest.raises(botocore.exceptions.ClientError):
                onboarder_writer.write_onboarding_status_to_dynamodb(
                    league_id="123",
                    platform="SLEEPER",
                    canonical_league_id="canonical-abc",
                    seasons=["2024"],
                    request_type="ONBOARD",
                )
