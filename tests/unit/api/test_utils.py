"""Tests for utility functions in main.py.

JSON logging (``JsonFormatter`` / ``setup_logger``) is shared code now exercised by
``tests/unit/common/test_logging_utils.py``.
"""

from decimal import Decimal
from unittest.mock import MagicMock, patch

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


class TestTrialUsedForLeague:
    def test_true_when_durable_marker_present(self, mock_table):
        from main import Platform, trial_used_for_league

        mock_table.get_item.return_value = {
            "Item": {"PK": "LEAGUE#123#PLATFORM#SLEEPER", "SK": "TRIAL_USED"}
        }
        assert trial_used_for_league("123", Platform.SLEEPER) is True
        _, kwargs = mock_table.get_item.call_args
        assert kwargs["Key"] == {
            "PK": "LEAGUE#123#PLATFORM#SLEEPER",
            "SK": "TRIAL_USED",
        }

    def test_false_when_marker_absent(self, mock_table):
        from main import Platform, trial_used_for_league

        mock_table.get_item.return_value = {}
        assert trial_used_for_league("123", Platform.SLEEPER) is False

    def test_raises_500_on_boto_error(self, mock_table):
        from main import Platform, trial_used_for_league

        mock_table.get_item.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "InternalError", "Message": "fail"}}, "GetItem"
        )
        with pytest.raises(HTTPException) as exc_info:
            trial_used_for_league("123", Platform.SLEEPER)
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


class TestUpdateLeagueCount:
    def test_increments_count(self, mock_table):
        from main import update_league_count

        update_league_count(1)
        mock_table.update_item.assert_called_once_with(
            Key={"PK": "APP#STATS", "SK": "LEAGUE_COUNT"},
            UpdateExpression="ADD league_count :delta",
            ExpressionAttributeValues={":delta": Decimal("1")},
        )

    def test_decrements_count(self, mock_table):
        from main import update_league_count

        update_league_count(-1)
        mock_table.update_item.assert_called_once_with(
            Key={"PK": "APP#STATS", "SK": "LEAGUE_COUNT"},
            UpdateExpression="ADD league_count :delta",
            ExpressionAttributeValues={":delta": Decimal("-1")},
        )


class TestGetStripeCustomerId:
    def test_returns_id_when_mapped(self, mock_table):
        from main import get_stripe_customer_id

        mock_table.get_item.return_value = {
            "Item": {"PK": "USER#u1", "SK": "USER", "stripe_customer_id": "cus_1"}
        }
        assert get_stripe_customer_id("u1") == "cus_1"

    def test_returns_none_when_unmapped(self, mock_table):
        from main import get_stripe_customer_id

        mock_table.get_item.return_value = {}
        assert get_stripe_customer_id("u1") is None

    def test_raises_500_on_boto_error(self, mock_table):
        from main import get_stripe_customer_id

        mock_table.get_item.side_effect = _boto_error()
        with pytest.raises(HTTPException) as exc:
            get_stripe_customer_id("u1")
        assert exc.value.status_code == 500


class TestGetOrCreateStripeCustomer:
    def test_returns_existing_without_creating(self, mock_table):
        from main import get_or_create_stripe_customer

        mock_table.get_item.return_value = {"Item": {"stripe_customer_id": "cus_1"}}
        with patch("main.stripe") as mock_stripe:
            assert get_or_create_stripe_customer("u1") == "cus_1"
            mock_stripe.Customer.create.assert_not_called()

    def test_creates_and_persists_when_absent(self, mock_table):
        from main import get_or_create_stripe_customer

        mock_table.get_item.return_value = {}
        with patch("main.stripe") as mock_stripe:
            mock_stripe.Customer.create.return_value = {"id": "cus_new"}
            assert get_or_create_stripe_customer("u1") == "cus_new"
        _, create_kwargs = mock_stripe.Customer.create.call_args
        assert create_kwargs["idempotency_key"] == "customer:u1"
        _, put_kwargs = mock_table.put_item.call_args
        assert put_kwargs["ConditionExpression"] == "attribute_not_exists(PK)"
        assert put_kwargs["Item"]["stripe_customer_id"] == "cus_new"

    def test_race_returns_existing_mapping(self, mock_table):
        from main import get_or_create_stripe_customer

        # First read: unmapped. Second read (after the conditional put loses the
        # race): the mapping a concurrent request wrote.
        mock_table.get_item.side_effect = [
            {},
            {"Item": {"stripe_customer_id": "cus_winner"}},
        ]
        mock_table.put_item.side_effect = _conditional_error()
        with patch("main.stripe") as mock_stripe:
            mock_stripe.Customer.create.return_value = {"id": "cus_mine"}
            assert get_or_create_stripe_customer("u1") == "cus_winner"

    def test_raises_500_on_put_boto_error(self, mock_table):
        from main import get_or_create_stripe_customer

        mock_table.get_item.return_value = {}
        mock_table.put_item.side_effect = _boto_error()
        with patch("main.stripe") as mock_stripe:
            mock_stripe.Customer.create.return_value = {"id": "cus_new"}
            with pytest.raises(HTTPException) as exc:
                get_or_create_stripe_customer("u1")
        assert exc.value.status_code == 500


class TestClaimPendingCheckout:
    def test_claims_slot_returns_true(self, mock_table):
        from main import claim_pending_checkout

        assert claim_pending_checkout("canonical-abc", "tok123", "user-1") is True
        _, kwargs = mock_table.update_item.call_args
        cond = kwargs["ConditionExpression"]
        assert "attribute_not_exists(stripe_subscription_id)" in cond
        assert "pending_checkout.expires_at < :now" in cond
        # Same-user re-claim: the initiating user can overwrite their own marker.
        assert "pending_checkout.user_id = :uid" in cond
        values = kwargs["ExpressionAttributeValues"]
        assert values[":uid"] == "user-1"
        pc = values[":pc"]
        assert pc["token"] == "tok123"
        assert pc["user_id"] == "user-1"
        assert "expires_at" in pc

    def test_returns_false_when_slot_taken(self, mock_table):
        from main import claim_pending_checkout

        mock_table.update_item.side_effect = _conditional_error()
        assert claim_pending_checkout("canonical-abc", "tok123", "user-1") is False

    def test_raises_500_on_boto_error(self, mock_table):
        from main import claim_pending_checkout

        mock_table.update_item.side_effect = _boto_error()
        with pytest.raises(HTTPException) as exc:
            claim_pending_checkout("canonical-abc", "tok123", "user-1")
        assert exc.value.status_code == 500


class TestRequireActiveSubscription:
    def _meta(self, end_time):
        item = {"PK": "LEAGUE#canonical-abc", "SK": "METADATA"}
        if end_time is not None:
            item["subscription_end_time"] = end_time
        return item

    def test_future_end_time_passes(self, mock_table):
        from main import require_active_subscription

        mock_table.get_item.return_value = {
            "Item": self._meta("2999-01-01T00:00:00+00:00")
        }
        # Should not raise.
        require_active_subscription("canonical-abc")

    def test_past_end_time_raises_402(self, mock_table):
        from fastapi import HTTPException

        from main import require_active_subscription

        mock_table.get_item.return_value = {
            "Item": self._meta("2000-01-01T00:00:00+00:00")
        }
        with pytest.raises(HTTPException) as exc:
            require_active_subscription("canonical-abc")
        assert exc.value.status_code == 402

    def test_absent_end_time_raises_402(self, mock_table):
        from fastapi import HTTPException

        from main import require_active_subscription

        mock_table.get_item.return_value = {"Item": self._meta(None)}
        with pytest.raises(HTTPException) as exc:
            require_active_subscription("canonical-abc")
        assert exc.value.status_code == 402

    def test_unparseable_end_time_raises_402(self, mock_table):
        from fastapi import HTTPException

        from main import require_active_subscription

        mock_table.get_item.return_value = {"Item": self._meta("not-a-date")}
        with pytest.raises(HTTPException) as exc:
            require_active_subscription("canonical-abc")
        assert exc.value.status_code == 402

    def test_uses_provided_metadata_without_fetching(self, mock_table):
        from main import require_active_subscription

        # Pre-fetched metadata short-circuits the DynamoDB read.
        require_active_subscription(
            "canonical-abc", metadata=self._meta("2999-01-01T00:00:00+00:00")
        )
        mock_table.get_item.assert_not_called()

    def test_noop_when_billing_disabled(self, mock_table):
        # Billing feature-flagged off (BE-017): the gate is a no-op, so an expired
        # (here absent) subscription does not raise and no METADATA read happens.
        from common import feature_flags
        from main import require_active_subscription

        feature_flags._override_for_testing({"billing": False})
        require_active_subscription("canonical-abc")
        mock_table.get_item.assert_not_called()


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
