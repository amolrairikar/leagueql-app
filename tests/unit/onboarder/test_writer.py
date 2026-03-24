import json
import os
from unittest.mock import MagicMock, patch

import botocore.exceptions
import pytest

from onboarder.writer import upload_results_to_s3, write_onboarding_job_id_to_dynamodb


class TestUploadResultsToS3:
    def test_uploads_json_to_s3(self):
        mock_s3 = MagicMock()
        results = [{"season": "2023", "data_type": "league_information", "data": {}}]

        with patch("onboarder.writer.boto3.client", return_value=mock_s3):
            upload_results_to_s3(
                results=results,
                bucket_name="my-bucket",
                key_name="raw-api-data/ESPN/123/onboard.json",
            )

        mock_s3.put_object.assert_called_once_with(
            Bucket="my-bucket",
            Key="raw-api-data/ESPN/123/onboard.json",
            Body=json.dumps(results),
            ContentType="application/json",
        )

    def test_serializes_results_as_json(self):
        mock_s3 = MagicMock()
        results = [{"key": "value"}]

        with patch("onboarder.writer.boto3.client", return_value=mock_s3):
            upload_results_to_s3(
                results=results,
                bucket_name="bucket",
                key_name="key/path.json",
            )

        call_kwargs = mock_s3.put_object.call_args[1]
        assert call_kwargs["Body"] == json.dumps(results)
        assert call_kwargs["ContentType"] == "application/json"

    def test_raises_client_error_on_s3_failure(self):
        error = botocore.exceptions.ClientError(
            {"Error": {"Code": "InternalError", "Message": "fail"}}, "PutObject"
        )
        mock_s3 = MagicMock()
        mock_s3.put_object.side_effect = error

        with patch("onboarder.writer.boto3.client", return_value=mock_s3):
            with pytest.raises(botocore.exceptions.ClientError):
                upload_results_to_s3(results=[], bucket_name="b", key_name="k")


class TestWriteOnboardingJobIdToDynamoDB:
    def test_returns_job_id_on_success(self):
        mock_dynamodb = MagicMock()

        with (
            patch("onboarder.writer.boto3.client", return_value=mock_dynamodb),
            patch("onboarder.writer.uuid.uuid4", return_value="test-uuid"),
            patch.dict(os.environ, {"DYNAMODB_TABLE_NAME": "test-table"}),
        ):
            result = write_onboarding_job_id_to_dynamodb()

        assert result == "test-uuid"
        mock_dynamodb.put_item.assert_called_once()

    def test_raises_key_error_when_env_var_missing(self):
        mock_dynamodb = MagicMock()

        with patch("onboarder.writer.boto3.client", return_value=mock_dynamodb):
            with pytest.raises(KeyError, match="DYNAMODB_TABLE_NAME"):
                write_onboarding_job_id_to_dynamodb()

    def test_raises_client_error_on_dynamodb_failure(self):
        error = botocore.exceptions.ClientError(
            {"Error": {"Code": "InternalError", "Message": "fail"}}, "PutItem"
        )
        mock_dynamodb = MagicMock()
        mock_dynamodb.put_item.side_effect = error

        with (
            patch("onboarder.writer.boto3.client", return_value=mock_dynamodb),
            patch.dict(os.environ, {"DYNAMODB_TABLE_NAME": "test-table"}),
        ):
            with pytest.raises(botocore.exceptions.ClientError):
                write_onboarding_job_id_to_dynamodb()
