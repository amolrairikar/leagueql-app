"""Tests for utility functions in main.py.

JSON logging (``JsonFormatter`` / ``setup_logger``) is shared code now exercised by
``tests/unit/common/test_logging_utils.py``.
"""

from decimal import Decimal
from unittest.mock import MagicMock

import botocore.exceptions
import pytest
from fastapi import HTTPException


def _conditional_error() -> botocore.exceptions.ClientError:
    """A DynamoDB ClientError representing a failed ConditionExpression."""
    return botocore.exceptions.ClientError(
        {"Error": {"Code": "ConditionalCheckFailedException", "Message": "x"}},
        "UpdateItem",
    )


def _boto_error() -> botocore.exceptions.ClientError:
    """A generic (non-conditional) DynamoDB ClientError."""
    return botocore.exceptions.ClientError(
        {"Error": {"Code": "ProvisionedThroughputExceededException", "Message": "x"}},
        "UpdateItem",
    )


@pytest.fixture(autouse=True)
def import_main():
    import main  # noqa: F401


def test_convert_decimals_flat_dict():
    from main import convert_decimals

    result = convert_decimals({"score": Decimal("105.75"), "week": 1})
    assert result == {"score": 105.75, "week": 1}


def test_convert_decimals_nested():
    from main import convert_decimals

    result = convert_decimals({"outer": {"inner": Decimal("3.14")}})
    assert result == {"outer": {"inner": 3.14}}


def test_convert_decimals_list():
    from main import convert_decimals

    result = convert_decimals([Decimal("1.1"), Decimal("2.2"), 3])
    assert result == [1.1, 2.2, 3]


def test_convert_decimals_passthrough():
    from main import convert_decimals

    assert convert_decimals("hello") == "hello"
    assert convert_decimals(42) == 42
    assert convert_decimals(None) is None


class TestLookupLeague:
    def test_returns_canonical_id(self, mock_table, league_lookup_item):
        from main import Platform, lookup_league

        mock_table.get_item.return_value = {"Item": league_lookup_item}
        result = lookup_league("123", Platform.SLEEPER)
        assert result == "canonical-abc"

    def test_raises_404_when_not_found(self, mock_table):
        from main import Platform, lookup_league

        mock_table.get_item.return_value = {}
        with pytest.raises(HTTPException) as exc_info:
            lookup_league("999", Platform.SLEEPER)
        assert exc_info.value.status_code == 404

    def test_raises_500_when_canonical_id_missing(self, mock_table):
        from main import Platform, lookup_league

        mock_table.get_item.return_value = {
            "Item": {"PK": "LEAGUE#123#PLATFORM#SLEEPER", "SK": "LEAGUE_LOOKUP"}
        }
        with pytest.raises(HTTPException) as exc_info:
            lookup_league("123", Platform.SLEEPER)
        assert exc_info.value.status_code == 500

    def test_raises_500_on_boto_error(self, mock_table):
        from main import Platform, lookup_league

        mock_table.get_item.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "InternalError", "Message": "fail"}}, "GetItem"
        )
        with pytest.raises(HTTPException) as exc_info:
            lookup_league("123", Platform.SLEEPER)
        assert exc_info.value.status_code == 500


class TestGetLeagueMetadata:
    def test_returns_item(self, mock_table, league_metadata_item):
        from main import get_league_metadata

        mock_table.get_item.return_value = {"Item": league_metadata_item}
        result = get_league_metadata("canonical-abc")
        assert result["league_name"] == "Test League"

    def test_raises_500_when_not_found(self, mock_table):
        from main import get_league_metadata

        mock_table.get_item.return_value = {}
        with pytest.raises(HTTPException) as exc_info:
            get_league_metadata("canonical-abc")
        assert exc_info.value.status_code == 500

    def test_raises_500_on_boto_error(self, mock_table):
        from main import get_league_metadata

        mock_table.get_item.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "InternalError", "Message": "fail"}}, "GetItem"
        )
        with pytest.raises(HTTPException) as exc_info:
            get_league_metadata("canonical-abc")
        assert exc_info.value.status_code == 500


class TestGetLeagueSeasons:
    def test_returns_sorted_seasons(self, mock_table):
        from main import get_league_seasons

        mock_table.query.return_value = {
            "Items": [
                {"seasons": {"2024", "2022"}},
                {"seasons": {"2023"}},
            ]
        }
        result = get_league_seasons("canonical-abc")
        assert result == ["2022", "2023", "2024"]

    def test_merges_seasons_across_items(self, mock_table):
        from main import get_league_seasons

        mock_table.query.return_value = {
            "Items": [
                {"seasons": {"2021"}},
                {"seasons": {"2021", "2022"}},
            ]
        }
        result = get_league_seasons("canonical-abc")
        assert result == ["2021", "2022"]

    def test_raises_500_when_no_items(self, mock_table):
        from main import get_league_seasons

        mock_table.query.return_value = {"Items": []}
        with pytest.raises(HTTPException) as exc_info:
            get_league_seasons("canonical-abc")
        assert exc_info.value.status_code == 500

    def test_raises_500_on_boto_error(self, mock_table):
        from main import get_league_seasons

        mock_table.query.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "InternalError", "Message": "fail"}}, "Query"
        )
        with pytest.raises(HTTPException) as exc_info:
            get_league_seasons("canonical-abc")
        assert exc_info.value.status_code == 500


class TestRequireLeagueOwner:
    def _meta(self, owner):
        item = {"PK": "LEAGUE#canonical-abc", "SK": "METADATA"}
        if owner is not None:
            item["owner_user_id"] = owner
        return item

    def test_owner_match_passes(self):
        from main import require_league_owner

        require_league_owner("canonical-abc", "user_1", metadata=self._meta("user_1"))

    def test_owner_mismatch_raises_403(self):
        from fastapi import HTTPException
        from main import require_league_owner

        with pytest.raises(HTTPException) as exc:
            require_league_owner(
                "canonical-abc", "user_2", metadata=self._meta("user_1")
            )
        assert exc.value.status_code == 403

    def test_absent_owner_raises_403(self):
        from fastapi import HTTPException
        from main import require_league_owner

        with pytest.raises(HTTPException) as exc:
            require_league_owner("canonical-abc", "user_1", metadata=self._meta(None))
        assert exc.value.status_code == 403

    def test_reads_metadata_when_not_provided(self, mock_table):
        from main import require_league_owner

        mock_table.get_item.return_value = {"Item": self._meta("user_1")}
        require_league_owner("canonical-abc", "user_1")
        mock_table.get_item.assert_called_once()

    def test_provided_metadata_short_circuits_read(self, mock_table):
        from main import require_league_owner

        require_league_owner("canonical-abc", "user_1", metadata=self._meta("user_1"))
        mock_table.get_item.assert_not_called()


class TestRequireLeagueMember:
    def _meta(self, owner=None, members=None):
        item = {"PK": "LEAGUE#canonical-abc", "SK": "METADATA"}
        if owner is not None:
            item["owner_user_id"] = owner
        if members is not None:
            item["members"] = members
        return item

    def test_sleeper_is_noop(self, mock_table):
        from main import Platform, require_league_member

        # No metadata fetch for Sleeper, and a non-member is allowed.
        require_league_member("canonical-abc", "stranger", Platform.SLEEPER)
        mock_table.get_item.assert_not_called()

    def test_espn_owner_allowed(self):
        from main import Platform, require_league_member

        require_league_member(
            "canonical-abc",
            "user_1",
            Platform.ESPN,
            metadata=self._meta(owner="user_1"),
        )

    def test_espn_member_allowed(self):
        from main import Platform, require_league_member

        require_league_member(
            "canonical-abc",
            "user_2",
            Platform.ESPN,
            metadata=self._meta(owner="user_1", members={"user_2"}),
        )

    def test_espn_non_member_raises_403(self):
        from fastapi import HTTPException
        from main import Platform, require_league_member

        with pytest.raises(HTTPException) as exc:
            require_league_member(
                "canonical-abc",
                "stranger",
                Platform.ESPN,
                metadata=self._meta(owner="user_1", members={"user_2"}),
            )
        assert exc.value.status_code == 403

    def test_espn_missing_members_treated_as_empty(self):
        from fastapi import HTTPException
        from main import Platform, require_league_member

        with pytest.raises(HTTPException) as exc:
            require_league_member(
                "canonical-abc",
                "stranger",
                Platform.ESPN,
                metadata=self._meta(owner="user_1"),
            )
        assert exc.value.status_code == 403

    def test_espn_reads_metadata_when_not_provided(self, mock_table):
        from main import Platform, require_league_member

        mock_table.get_item.return_value = {"Item": self._meta(owner="user_1")}
        require_league_member("canonical-abc", "user_1", Platform.ESPN)
        mock_table.get_item.assert_called_once()


class TestAddLeagueMember:
    def test_adds_member_via_update_item(self, mock_table):
        from main import add_league_member

        add_league_member("canonical-abc", "user_2")
        mock_table.update_item.assert_called_once()
        kwargs = mock_table.update_item.call_args.kwargs
        assert kwargs["Key"] == {
            "PK": "LEAGUE#canonical-abc",
            "SK": "METADATA",
        }
        assert "ADD members" in kwargs["UpdateExpression"]
        assert kwargs["ExpressionAttributeValues"][":m"] == {"user_2"}

    def test_client_error_raises_500(self, mock_table):
        import botocore.exceptions
        from fastapi import HTTPException
        from main import add_league_member

        mock_table.update_item.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "InternalError", "Message": "x"}}, "UpdateItem"
        )
        with pytest.raises(HTTPException) as exc:
            add_league_member("canonical-abc", "user_2")
        assert exc.value.status_code == 500


class TestDeleteLeagueHelpers:
    def _setup_writer(self, mock_table):
        mock_writer = MagicMock()
        mock_table.batch_writer.return_value.__enter__ = MagicMock(
            return_value=mock_writer
        )
        mock_table.batch_writer.return_value.__exit__ = MagicMock(return_value=False)
        return mock_writer

    def test_query_all_keys_paginates(self, mock_table):
        from main import _query_all_keys

        mock_table.query.side_effect = [
            {
                "Items": [{"PK": "LEAGUE#abc", "SK": "TEAMS#2024"}],
                "LastEvaluatedKey": {"PK": "x", "SK": "y"},
            },
            {"Items": [{"PK": "LEAGUE#abc", "SK": "TEAMS#2025"}]},
        ]
        keys = _query_all_keys({"KeyConditionExpression": "ignored"})
        assert keys == [
            {"PK": "LEAGUE#abc", "SK": "TEAMS#2024"},
            {"PK": "LEAGUE#abc", "SK": "TEAMS#2025"},
        ]
        assert mock_table.query.call_count == 2

    def test_collect_league_keys_merges_pk_and_gsi(self, mock_table):
        from main import collect_league_keys

        mock_table.query.side_effect = [
            # canonical PK items (METADATA, views, orphan-prone migration item)
            {
                "Items": [
                    {"PK": "LEAGUE#canonical-abc", "SK": "METADATA"},
                    {
                        "PK": "LEAGUE#canonical-abc",
                        "SK": "PLATFORM_MIGRATION#SLEEPER#ESPN",
                    },
                ]
            },
            # GSI1 LEAGUE_LOOKUP items on their own PK
            {"Items": [{"PK": "LEAGUE#123#PLATFORM#SLEEPER", "SK": "LEAGUE_LOOKUP"}]},
        ]
        keys = collect_league_keys("canonical-abc")
        assert {"PK": "LEAGUE#canonical-abc", "SK": "METADATA"} in keys
        assert {
            "PK": "LEAGUE#canonical-abc",
            "SK": "PLATFORM_MIGRATION#SLEEPER#ESPN",
        } in keys
        assert {"PK": "LEAGUE#123#PLATFORM#SLEEPER", "SK": "LEAGUE_LOOKUP"} in keys

    def test_delete_all_league_items_deletes_everything(
        self, mock_table, mock_time_sleep
    ):
        from main import delete_all_league_items

        writer = self._setup_writer(mock_table)
        mock_table.query.side_effect = [
            {"Items": [{"PK": "LEAGUE#canonical-abc", "SK": "METADATA"}]},
            {"Items": [{"PK": "LEAGUE#123#PLATFORM#SLEEPER", "SK": "LEAGUE_LOOKUP"}]},
            {"Items": []},
            {"Items": []},
        ]
        delete_all_league_items("canonical-abc")
        writer.delete_item.assert_any_call(
            Key={"PK": "LEAGUE#canonical-abc", "SK": "METADATA"}
        )
        writer.delete_item.assert_any_call(
            Key={"PK": "LEAGUE#123#PLATFORM#SLEEPER", "SK": "LEAGUE_LOOKUP"}
        )

    def test_delete_all_league_items_noop_when_empty(self, mock_table, mock_time_sleep):
        from main import delete_all_league_items

        writer = self._setup_writer(mock_table)
        mock_table.query.return_value = {"Items": []}
        delete_all_league_items("canonical-abc")
        writer.delete_item.assert_not_called()
        mock_time_sleep.assert_not_called()

    def test_delete_all_league_items_retries_until_clean(
        self, mock_table, mock_time_sleep
    ):
        from main import delete_all_league_items

        writer = self._setup_writer(mock_table)
        mock_table.query.side_effect = [
            # pass 1: an item on the canonical PK, GSI1 empty
            {"Items": [{"PK": "LEAGUE#canonical-abc", "SK": "METADATA"}]},
            {"Items": []},
            # pass 2: GSI1 was lagging, a lookup item now surfaces
            {"Items": []},
            {"Items": [{"PK": "LEAGUE#123#PLATFORM#SLEEPER", "SK": "LEAGUE_LOOKUP"}]},
            # pass 3: clean
            {"Items": []},
            {"Items": []},
        ]
        delete_all_league_items("canonical-abc")
        assert writer.delete_item.call_count == 2

    def test_delete_all_league_items_exits_clean_after_final_pass(
        self, mock_table, mock_time_sleep
    ):
        # With a single attempt that deletes items, the loop runs to completion and
        # the post-loop verification finds nothing remaining -> clean exit (no raise).
        from main import delete_all_league_items

        writer = self._setup_writer(mock_table)
        mock_table.query.side_effect = [
            # attempt 1 collect: one item on the PK, GSI empty
            {"Items": [{"PK": "LEAGUE#canonical-abc", "SK": "METADATA"}]},
            {"Items": []},
            # post-loop verification: clean
            {"Items": []},
            {"Items": []},
        ]
        delete_all_league_items("canonical-abc", max_attempts=1)
        writer.delete_item.assert_called_once()

    def test_delete_all_league_items_raises_when_orphans_remain(
        self, mock_table, mock_time_sleep, mock_sns_client
    ):
        from main import delete_all_league_items

        self._setup_writer(mock_table)
        # Every collect pass keeps returning the same item: it never clears.
        mock_table.query.return_value = {
            "Items": [{"PK": "LEAGUE#canonical-abc", "SK": "TEAMS#2024"}]
        }
        with pytest.raises(HTTPException) as exc_info:
            delete_all_league_items("canonical-abc", max_attempts=2)
        assert exc_info.value.status_code == 500
        assert "fully delete" in exc_info.value.detail.lower()
        # Orphaned items should trigger an SNS failure notification.
        mock_sns_client.publish.assert_called_once()
        kwargs = mock_sns_client.publish.call_args.kwargs
        assert "canonical-abc" in kwargs["Message"]
        assert "TEAMS#2024" in kwargs["Message"]

    def test_delete_all_league_items_raises_on_query_error(self, mock_table):
        from main import delete_all_league_items

        mock_table.query.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "InternalError", "Message": "fail"}}, "Query"
        )
        with pytest.raises(botocore.exceptions.ClientError):
            delete_all_league_items("canonical-abc")


class TestOwnerHasOtherYahooLeagues:
    def test_true_when_another_yahoo_league_owned(self, mock_table):
        from main import owner_has_other_yahoo_leagues

        mock_table.query.return_value = {
            "Items": [
                {"PK": "LEAGUE#deleted", "platform": "YAHOO"},
                {"PK": "LEAGUE#other", "platform": "YAHOO"},
            ]
        }
        assert owner_has_other_yahoo_leagues("user_1", "deleted") is True

    def test_false_when_only_the_excluded_league(self, mock_table):
        from main import owner_has_other_yahoo_leagues

        mock_table.query.return_value = {
            "Items": [{"PK": "LEAGUE#deleted", "platform": "YAHOO"}]
        }
        assert owner_has_other_yahoo_leagues("user_1", "deleted") is False

    def test_false_when_other_leagues_not_yahoo(self, mock_table):
        from main import owner_has_other_yahoo_leagues

        mock_table.query.return_value = {
            "Items": [
                {"PK": "LEAGUE#espn", "platform": "ESPN"},
                {"PK": "LEAGUE#sleeper", "platform": "SLEEPER"},
            ]
        }
        assert owner_has_other_yahoo_leagues("user_1", "deleted") is False

    def test_migrated_away_from_yahoo_does_not_count(self, mock_table):
        from main import owner_has_other_yahoo_leagues

        # A league migrated away from Yahoo (active_platform SLEEPER) no longer
        # needs the Yahoo link, so it does not keep the token alive.
        mock_table.query.return_value = {
            "Items": [
                {
                    "PK": "LEAGUE#migrated_away",
                    "platform": "YAHOO",
                    "active_platform": "SLEEPER",
                }
            ]
        }
        assert owner_has_other_yahoo_leagues("user_1", "deleted") is False

    def test_migrated_to_yahoo_counts(self, mock_table):
        from main import owner_has_other_yahoo_leagues

        # A league migrated *to* Yahoo (active_platform YAHOO) does need the link.
        mock_table.query.return_value = {
            "Items": [
                {
                    "PK": "LEAGUE#migrated_to",
                    "platform": "SLEEPER",
                    "active_platform": "YAHOO",
                }
            ]
        }
        assert owner_has_other_yahoo_leagues("user_1", "deleted") is True

    def test_paginates_over_last_evaluated_key(self, mock_table):
        from main import owner_has_other_yahoo_leagues

        mock_table.query.side_effect = [
            {
                "Items": [{"PK": "LEAGUE#deleted", "platform": "YAHOO"}],
                "LastEvaluatedKey": {"k": 1},
            },
            {"Items": [{"PK": "LEAGUE#other", "platform": "YAHOO"}]},
        ]
        assert owner_has_other_yahoo_leagues("user_1", "deleted") is True
        assert mock_table.query.call_count == 2


class TestPublishFailure:
    # The shared publish/no-op/error-swallow behavior is covered by
    # tests/unit/common/test_sns.py; here we verify the API binds its own subject.
    def test_publish_failure_binds_api_subject(self, mock_sns_client):
        from main import publish_failure

        publish_failure("something broke")
        mock_sns_client.publish.assert_called_once()
        kwargs = mock_sns_client.publish.call_args.kwargs
        assert kwargs["Subject"] == "LeagueQL API Failure"
        assert "something broke" in kwargs["Message"]


class TestJobStatusHelpers:
    def test_create_job_status_omits_optional_fields(self, mock_table):
        # With no league_id/platform, the IN_PROGRESS item carries only the
        # canonical id, exercising the optional-field skip branches.
        from main import create_job_status

        create_job_status(
            correlation_id="corr-1",
            request_type="ONBOARD",
            canonical_league_id="canonical-abc",
        )
        item = mock_table.put_item.call_args.kwargs["Item"]
        assert item["PK"] == "JOB#corr-1"
        assert item["status"] == "IN_PROGRESS"
        assert "league_id" not in item
        assert "platform" not in item
        assert item["canonical_league_id"] == "canonical-abc"

    def test_create_job_status_includes_optional_fields(self, mock_table):
        from main import create_job_status

        create_job_status(
            correlation_id="corr-1",
            request_type="REFRESH",
            league_id="123",
            platform="SLEEPER",
        )
        item = mock_table.put_item.call_args.kwargs["Item"]
        assert item["league_id"] == "123"
        assert item["platform"] == "SLEEPER"

    def test_create_job_status_swallows_client_error(self, mock_table):
        # A failure to write JOB_STATUS must not propagate (best-effort).
        from main import create_job_status

        mock_table.put_item.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "InternalError", "Message": "fail"}}, "PutItem"
        )
        create_job_status(correlation_id="corr-1", request_type="ONBOARD")

    def test_get_job_status_returns_item(self, mock_table):
        from main import get_job_status

        mock_table.get_item.return_value = {"Item": {"status": "COMPLETED"}}
        assert get_job_status("corr-1") == {"status": "COMPLETED"}

    def test_get_job_status_returns_none_when_absent(self, mock_table):
        from main import get_job_status

        mock_table.get_item.return_value = {}
        assert get_job_status("corr-1") is None

    def test_get_job_status_raises_500_on_client_error(self, mock_table):
        from fastapi import HTTPException
        from main import get_job_status

        mock_table.get_item.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "InternalError", "Message": "fail"}}, "GetItem"
        )
        with pytest.raises(HTTPException) as exc_info:
            get_job_status("corr-1")
        assert exc_info.value.status_code == 500

    def test_set_active_job_updates_metadata(self, mock_table):
        from main import set_active_job

        set_active_job("canonical-abc", "corr-1")
        kwargs = mock_table.update_item.call_args.kwargs
        assert kwargs["ExpressionAttributeValues"] == {":j": "corr-1"}

    def test_set_active_job_swallows_client_error(self, mock_table):
        # Setting the active-job pointer is best-effort; errors are logged only.
        from main import set_active_job

        mock_table.update_item.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "InternalError", "Message": "fail"}}, "UpdateItem"
        )
        set_active_job("canonical-abc", "corr-1")


class TestOwnerHasOtherOptedinEspnLeagues:
    # GSI3 does not project auto_refresh_enabled, so the helper reads each candidate ESPN
    # league's METADATA (get_item) to check the flag.
    def test_true_when_another_optedin_espn_league(self, mock_table):
        from main import owner_has_other_optedin_espn_leagues

        mock_table.query.return_value = {
            "Items": [
                {"PK": "LEAGUE#deleted", "platform": "ESPN"},
                {"PK": "LEAGUE#other", "platform": "ESPN"},
            ]
        }
        # The excluded league is skipped by PK; the other's METADATA reads opted-in.
        mock_table.get_item.return_value = {"Item": {"auto_refresh_enabled": True}}
        assert owner_has_other_optedin_espn_leagues("user_1", "deleted") is True
        mock_table.get_item.assert_called_once_with(
            Key={"PK": "LEAGUE#other", "SK": "METADATA"}
        )

    def test_false_when_only_the_excluded_league(self, mock_table):
        from main import owner_has_other_optedin_espn_leagues

        mock_table.query.return_value = {
            "Items": [{"PK": "LEAGUE#deleted", "platform": "ESPN"}]
        }
        assert owner_has_other_optedin_espn_leagues("user_1", "deleted") is False
        mock_table.get_item.assert_not_called()

    def test_false_when_other_espn_not_opted_in(self, mock_table):
        from main import owner_has_other_optedin_espn_leagues

        # Another ESPN league exists but its METADATA is not opted in, so it does not
        # keep the stored cookies alive.
        mock_table.query.return_value = {
            "Items": [
                {"PK": "LEAGUE#other", "platform": "ESPN"},
                {"PK": "LEAGUE#other2", "platform": "ESPN"},
            ]
        }
        mock_table.get_item.return_value = {"Item": {}}
        assert owner_has_other_optedin_espn_leagues("user_1", "deleted") is False

    def test_false_when_other_leagues_not_espn(self, mock_table):
        from main import owner_has_other_optedin_espn_leagues

        mock_table.query.return_value = {
            "Items": [
                {"PK": "LEAGUE#yahoo", "platform": "YAHOO"},
                {"PK": "LEAGUE#sleeper", "platform": "SLEEPER"},
            ]
        }
        assert owner_has_other_optedin_espn_leagues("user_1", "deleted") is False
        # Non-ESPN leagues never trigger the METADATA read.
        mock_table.get_item.assert_not_called()

    def test_migrated_to_espn_counts(self, mock_table):
        from main import owner_has_other_optedin_espn_leagues

        mock_table.query.return_value = {
            "Items": [
                {
                    "PK": "LEAGUE#migrated_to",
                    "platform": "SLEEPER",
                    "active_platform": "ESPN",
                }
            ]
        }
        mock_table.get_item.return_value = {"Item": {"auto_refresh_enabled": True}}
        assert owner_has_other_optedin_espn_leagues("user_1", "deleted") is True

    def test_paginates_over_last_evaluated_key(self, mock_table):
        from main import owner_has_other_optedin_espn_leagues

        mock_table.query.side_effect = [
            {
                "Items": [{"PK": "LEAGUE#deleted", "platform": "ESPN"}],
                "LastEvaluatedKey": {"k": 1},
            },
            {"Items": [{"PK": "LEAGUE#other", "platform": "ESPN"}]},
        ]
        mock_table.get_item.return_value = {"Item": {"auto_refresh_enabled": True}}
        assert owner_has_other_optedin_espn_leagues("user_1", "deleted") is True
        assert mock_table.query.call_count == 2
