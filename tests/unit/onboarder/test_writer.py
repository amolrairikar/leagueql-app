import json
from unittest.mock import MagicMock, patch

from onboarder.writer import upload_results_to_s3


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
