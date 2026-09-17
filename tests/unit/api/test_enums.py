"""Tests for enum classes in main.py."""

import pytest


class TestPlatformEnum:
    def test_valid_uppercase(self):
        from main import Platform

        assert Platform("SLEEPER") == Platform.SLEEPER
        assert Platform("ESPN") == Platform.ESPN
        assert Platform("YAHOO") == Platform.YAHOO

    def test_valid_lowercase(self):
        from main import Platform

        assert Platform("sleeper") == Platform.SLEEPER
        assert Platform("espn") == Platform.ESPN
        assert Platform("yahoo") == Platform.YAHOO

    def test_valid_mixed_case(self):
        from main import Platform

        assert Platform("Sleeper") == Platform.SLEEPER
        assert Platform("Espn") == Platform.ESPN
        assert Platform("Yahoo") == Platform.YAHOO

    def test_invalid_value_returns_none(self):
        from main import Platform

        assert Platform._missing_("MYFANTASY") is None

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
            ("TRANSACTIONS", "TRANSACTIONS"),
        ],
    )
    def test_valid_values(self, value, expected):
        from main import QueryType

        assert QueryType(value).value == expected

    def test_case_insensitive(self):
        from main import QueryType

        assert QueryType("teams") == QueryType.TEAMS
        assert QueryType("matchups") == QueryType.MATCHUPS
