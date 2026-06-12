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

    def test_reprocess_all_stamps_manifest_metadata(self, onboarder_writer):
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
                reprocess_all=True,
            )
        manifest_call = next(
            c
            for c in mock_s3.put_object.call_args_list
            if "manifest.json" in c[1]["Key"]
        )
        assert manifest_call[1]["Metadata"]["reprocess_all"] == "true"

    def test_reprocess_all_absent_by_default(self, onboarder_writer):
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
        assert "reprocess_all" not in manifest_call[1]["Metadata"]

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


class TestWriteLeagueRecords:
    def test_onboard_writes_metadata_and_lookup(self, onboarder_writer, monkeypatch):
        monkeypatch.setenv("DYNAMODB_TABLE_NAME", "test-table")
        mock_ddb = MagicMock()
        with patch.object(onboarder_writer, "_dynamodb", mock_ddb):
            onboarder_writer.write_league_records(
                league_id="123",
                platform="SLEEPER",
                canonical_league_id="canonical-abc",
                seasons=["2024"],
                request_type="ONBOARD",
            )
        mock_ddb.transact_write_items.assert_called_once()
        items = mock_ddb.transact_write_items.call_args[1]["TransactItems"]
        assert len(items) == 2

    def test_onboard_writes_owner_and_seeds_members(
        self, onboarder_writer, monkeypatch
    ):
        # LQL-01 / BE-016: the onboarding owner is recorded and seeds members.
        monkeypatch.setenv("DYNAMODB_TABLE_NAME", "test-table")
        mock_ddb = MagicMock()
        with patch.object(onboarder_writer, "_dynamodb", mock_ddb):
            onboarder_writer.write_league_records(
                league_id="123",
                platform="ESPN",
                canonical_league_id="canonical-abc",
                seasons=["2024"],
                request_type="ONBOARD",
                owner_user_id="user_1",
            )
        metadata_item = mock_ddb.transact_write_items.call_args[1]["TransactItems"][0][
            "Put"
        ]["Item"]
        assert metadata_item["owner_user_id"] == {"S": "user_1"}
        assert metadata_item["members"] == {"SS": ["user_1"]}

    def test_onboard_without_owner_omits_owner_and_members(
        self, onboarder_writer, monkeypatch
    ):
        # System-initiated onboards (no owner) leave owner/members absent.
        monkeypatch.setenv("DYNAMODB_TABLE_NAME", "test-table")
        mock_ddb = MagicMock()
        with patch.object(onboarder_writer, "_dynamodb", mock_ddb):
            onboarder_writer.write_league_records(
                league_id="123",
                platform="SLEEPER",
                canonical_league_id="canonical-abc",
                seasons=["2024"],
                request_type="ONBOARD",
            )
        metadata_item = mock_ddb.transact_write_items.call_args[1]["TransactItems"][0][
            "Put"
        ]["Item"]
        assert "owner_user_id" not in metadata_item
        assert "members" not in metadata_item

    def test_onboard_never_writes_subscription_end_time(
        self, onboarder_writer, monkeypatch
    ):
        # subscription_end_time is set only server-side by the Stripe billing
        # webhook (BE-014 / BE-015). Onboarding must never write it — there is no
        # longer a client-supplied input that could (BE-001).
        monkeypatch.setenv("DYNAMODB_TABLE_NAME", "test-table")
        mock_ddb = MagicMock()
        with patch.object(onboarder_writer, "_dynamodb", mock_ddb):
            onboarder_writer.write_league_records(
                league_id="123",
                platform="SLEEPER",
                canonical_league_id="canonical-abc",
                seasons=["2024"],
                request_type="ONBOARD",
            )
        items = mock_ddb.transact_write_items.call_args[1]["TransactItems"]
        metadata_item = items[0]["Put"]["Item"]
        assert "subscription_end_time" not in metadata_item

    def test_refresh_does_not_touch_subscription_end_time(
        self, onboarder_writer, monkeypatch
    ):
        monkeypatch.setenv("DYNAMODB_TABLE_NAME", "test-table")
        mock_ddb = MagicMock()
        with patch.object(onboarder_writer, "_dynamodb", mock_ddb):
            onboarder_writer.write_league_records(
                league_id="123",
                platform="SLEEPER",
                canonical_league_id="canonical-abc",
                seasons=["2024"],
                request_type="REFRESH",
                is_new_season_refresh=False,
            )
        items = mock_ddb.transact_write_items.call_args[1]["TransactItems"]
        metadata_update = items[0]["Update"]
        assert "subscription_end_time" not in metadata_update["UpdateExpression"]

    def test_migrate_writes_only_lookup_no_metadata(
        self, onboarder_writer, monkeypatch
    ):
        # Status now lives in the JOB_STATUS item, so MIGRATE writes only the
        # LEAGUE_LOOKUP item — no METADATA update at all.
        monkeypatch.setenv("DYNAMODB_TABLE_NAME", "test-table")
        mock_ddb = MagicMock()
        with patch.object(onboarder_writer, "_dynamodb", mock_ddb):
            onboarder_writer.write_league_records(
                league_id="123",
                platform="SLEEPER",
                canonical_league_id="canonical-abc",
                seasons=["2024"],
                request_type="MIGRATE",
            )
        items = mock_ddb.transact_write_items.call_args[1]["TransactItems"]
        assert len(items) == 1
        assert items[0]["Put"]["Item"]["SK"] == {"S": "LEAGUE_LOOKUP"}

    def test_refresh_existing_season_uses_update(self, onboarder_writer, monkeypatch):
        # REFRESH now writes only the LEAGUE_LOOKUP item (status moved to
        # JOB_STATUS); an existing season updates the lookup in place.
        monkeypatch.setenv("DYNAMODB_TABLE_NAME", "test-table")
        mock_ddb = MagicMock()
        with patch.object(onboarder_writer, "_dynamodb", mock_ddb):
            onboarder_writer.write_league_records(
                league_id="123",
                platform="SLEEPER",
                canonical_league_id="canonical-abc",
                seasons=["2024"],
                request_type="REFRESH",
                is_new_season_refresh=False,
            )
        items = mock_ddb.transact_write_items.call_args[1]["TransactItems"]
        assert len(items) == 1
        assert "Update" in items[0]
        assert items[0]["Update"]["Key"]["SK"] == {"S": "LEAGUE_LOOKUP"}

    def test_refresh_new_season_uses_put(self, onboarder_writer, monkeypatch):
        monkeypatch.setenv("DYNAMODB_TABLE_NAME", "test-table")
        mock_ddb = MagicMock()
        with patch.object(onboarder_writer, "_dynamodb", mock_ddb):
            onboarder_writer.write_league_records(
                league_id="456",
                platform="SLEEPER",
                canonical_league_id="canonical-abc",
                seasons=["2025"],
                request_type="REFRESH",
                is_new_season_refresh=True,
            )
        items = mock_ddb.transact_write_items.call_args[1]["TransactItems"]
        assert len(items) == 1
        assert "Put" in items[0]
        assert items[0]["Put"]["Item"]["SK"] == {"S": "LEAGUE_LOOKUP"}

    def test_missing_env_var_raises_key_error(self, onboarder_writer, monkeypatch):
        monkeypatch.delenv("DYNAMODB_TABLE_NAME", raising=False)
        with pytest.raises(KeyError):
            onboarder_writer.write_league_records(
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
                onboarder_writer.write_league_records(
                    league_id="123",
                    platform="SLEEPER",
                    canonical_league_id="canonical-abc",
                    seasons=["2024"],
                    request_type="ONBOARD",
                )
