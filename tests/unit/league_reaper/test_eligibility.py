from datetime import UTC, datetime

import pytest

NOW = datetime(2027, 6, 15, 9, 0, tzinfo=UTC)
ONE_YEAR_AGO = "2026-06-15T09:00:00+00:00"
JUST_UNDER = "2026-06-15T09:00:01+00:00"


class TestIsExpired:
    @pytest.mark.parametrize(
        ("metadata", "expected"),
        [
            ({"onboarded_at": ONE_YEAR_AGO}, True),
            ({"onboarded_at": JUST_UNDER}, False),
            ({"onboarded_at": "2024-01-01T00:00:00+00:00"}, True),
            # Naive and "Z" timestamps are UTC.
            ({"onboarded_at": "2026-06-15T09:00:00"}, True),
            ({"onboarded_at": "2026-06-15T09:00:00Z"}, True),
            (
                {
                    "onboarded_at": "2024-01-01T00:00:00+00:00",
                    "last_accessed_at": ONE_YEAR_AGO,
                },
                True,
            ),
            # Opened more than a year after onboarding, but recently: kept.
            (
                {
                    "onboarded_at": "2024-01-01T00:00:00+00:00",
                    "last_accessed_at": "2027-06-14T00:00:00+00:00",
                },
                False,
            ),
            ({}, False),
            ({"onboarded_at": "nope"}, False),
            ({"onboarded_at": 5}, False),
            ({"last_accessed_at": "2020-01-01T00:00:00+00:00"}, False),
            ({"onboarded_at": ONE_YEAR_AGO, "last_accessed_at": "nope"}, False),
            ({"onboarded_at": ONE_YEAR_AGO, "last_accessed_at": ""}, False),
        ],
    )
    def test_rule(self, eligibility, metadata, expected):
        assert eligibility.is_expired(metadata, NOW) is expected

    @pytest.mark.parametrize(
        ("now", "expected"),
        [
            (datetime(2029, 2, 28, 23, 59, tzinfo=UTC), False),
            (datetime(2029, 3, 1, 0, 0, tzinfo=UTC), True),
        ],
    )
    def test_leap_day_anniversary_is_march_first(self, eligibility, now, expected):
        metadata = {"onboarded_at": "2028-02-29T00:00:00+00:00"}
        assert eligibility.is_expired(metadata, now) is expected
