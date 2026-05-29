"""Tests for enum classes in main.py."""

import pytest


class TestPlatformEnum:
    def test_valid_uppercase(self):
        from main import Platform

        assert Platform("SLEEPER") == Platform.SLEEPER
        assert Platform("ESPN") == Platform.ESPN

    def test_valid_lowercase(self):
        from main import Platform

        assert Platform("sleeper") == Platform.SLEEPER
        assert Platform("espn") == Platform.ESPN

    def test_valid_mixed_case(self):
        from main import Platform

        assert Platform("Sleeper") == Platform.SLEEPER
        assert Platform("Espn") == Platform.ESPN

    def test_invalid_value_returns_none(self):
        from main import Platform

        assert Platform._missing_("YAHOO") is None

    def test_invalid_non_string_returns_none(self):
        from main import Platform

        assert Platform._missing_(123) is None


class TestRequestTypeEnum:
    def test_valid_values(self):
        from main import RequestType

        assert RequestType("ONBOARD") == RequestType.ONBOARD
        assert RequestType("REFRESH") == RequestType.REFRESH

    def test_case_insensitive(self):
        from main import RequestType

        assert RequestType("onboard") == RequestType.ONBOARD
        assert RequestType("refresh") == RequestType.REFRESH


class TestQueryTypeEnum:
    @pytest.mark.parametrize(
        "value,expected",
        [
            ("TEAMS", "TEAMS"),
            ("MATCHUPS", "MATCHUPS"),
            ("SEASON_STANDINGS", "SEASON_STANDINGS"),
            ("WEEKLY_STANDINGS", "WEEKLY_STANDINGS"),
            ("PLAYOFF_BRACKET", "PLAYOFF_BRACKET"),
            ("DRAFT", "DRAFT"),
        ],
    )
    def test_valid_values(self, value, expected):
        from main import QueryType

        assert QueryType(value).value == expected

    def test_case_insensitive(self):
        from main import QueryType

        assert QueryType("teams") == QueryType.TEAMS
        assert QueryType("matchups") == QueryType.MATCHUPS


class TestSubscriptionStatusEnum:
    @pytest.mark.parametrize(
        "value",
        ["FREE", "ACTIVE", "PAST_DUE", "CANCELED"],
    )
    def test_valid_values(self, value):
        from main import SubscriptionStatus

        assert SubscriptionStatus(value).value == value

    def test_case_insensitive(self):
        from main import SubscriptionStatus

        assert SubscriptionStatus("active") == SubscriptionStatus.ACTIVE
        assert SubscriptionStatus("past_due") == SubscriptionStatus.PAST_DUE

    def test_invalid_value_returns_none(self):
        from main import SubscriptionStatus

        assert SubscriptionStatus._missing_("PREMIUM") is None

    def test_default_is_active(self):
        from main import DEFAULT_SUBSCRIPTION_STATUS, SubscriptionStatus

        assert DEFAULT_SUBSCRIPTION_STATUS == SubscriptionStatus.ACTIVE
