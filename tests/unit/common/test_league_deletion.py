from unittest.mock import MagicMock

import pytest


@pytest.fixture
def league_deletion():
    from common import league_deletion

    return league_deletion


class TestDeleteLeagueRawData:
    def test_deletes_every_page(self, league_deletion):
        first = [{"Key": f"raw-api-data/abc/{i}.json"} for i in range(1000)]
        second = [{"Key": "raw-api-data/abc/last.json"}]
        s3 = MagicMock()
        s3.list_objects_v2.side_effect = [
            {"Contents": first, "IsTruncated": True, "NextContinuationToken": "t1"},
            {"Contents": second, "IsTruncated": False},
        ]
        s3.delete_objects.return_value = {}

        assert league_deletion.delete_league_raw_data(s3, "bucket", "abc") == 1001

        assert s3.list_objects_v2.call_args_list[1].kwargs == {
            "Bucket": "bucket",
            "Prefix": "raw-api-data/abc/",
            "MaxKeys": 1000,
            "ContinuationToken": "t1",
        }
        batches = [
            c.kwargs["Delete"]["Objects"] for c in s3.delete_objects.call_args_list
        ]
        assert batches == [first, second]

    def test_empty_prefix_deletes_nothing(self, league_deletion):
        s3 = MagicMock()
        s3.list_objects_v2.return_value = {}
        assert league_deletion.delete_league_raw_data(s3, "bucket", "abc") == 0
        s3.delete_objects.assert_not_called()

    def test_raises_when_s3_reports_errors(self, league_deletion):
        s3 = MagicMock()
        s3.list_objects_v2.return_value = {"Contents": [{"Key": "k"}]}
        s3.delete_objects.return_value = {"Errors": [{"Key": "k"}]}
        with pytest.raises(league_deletion.LeagueDeletionError):
            league_deletion.delete_league_raw_data(s3, "bucket", "abc")


class TestIterOwnerLeagueMetadata:
    def test_paginates_and_skips_every_excluded_league(self, league_deletion):
        table = MagicMock()
        table.query.side_effect = [
            {"Items": [{"PK": "LEAGUE#a"}], "LastEvaluatedKey": {"PK": "LEAGUE#a"}},
            {"Items": [{"PK": "LEAGUE#b"}, {"PK": "LEAGUE#c"}]},
        ]
        items = list(
            league_deletion.iter_owner_league_metadata(table, "user_1", {"a", "b"})
        )
        assert items == [{"PK": "LEAGUE#c"}]
        assert table.query.call_count == 2
