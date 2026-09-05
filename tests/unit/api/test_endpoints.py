"""Tests for FastAPI endpoint handlers in main.py."""

from datetime import datetime, timedelta, timezone
from typing import ClassVar
from unittest.mock import MagicMock, patch

import botocore.exceptions
import pytest


class TestHealthEndpoint:
    def test_health_check(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["detail"] == "Healthy!"


class TestSecurityHeaders:
    """Every response carries the hardening headers and a default-deny cache (backend/security-headers)."""

    EXPECTED: ClassVar = {
        "x-content-type-options": "nosniff",
        "content-security-policy": (
            "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
        ),
        "strict-transport-security": "max-age=63072000; includeSubDomains",
        "x-frame-options": "DENY",
    }

    def test_security_headers_present_on_every_response(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        for header, value in self.EXPECTED.items():
            assert response.headers.get(header) == value, dict(response.headers)

    def test_security_headers_present_on_error_response(self, client, mock_table):
        # 404 error responses are stamped too (the middleware wraps the whole app).
        mock_table.get_item.return_value = {}
        response = client.get("/leagues/999?platform=SLEEPER")
        assert response.status_code == 404
        for header, value in self.EXPECTED.items():
            assert response.headers.get(header) == value, dict(response.headers)

    def test_cache_control_defaults_to_no_store(self, client):
        # A route that sets no Cache-Control of its own falls back to no-store.
        response = client.get("/health")
        assert response.headers["cache-control"] == "no-store"

    def test_default_does_not_override_route_cache_control(
        self, client, mock_table, league_lookup_item
    ):
        # The query route's private, max-age=300 opt-in must survive the default.
        mock_table.get_item.return_value = {"Item": league_lookup_item}
        mock_table.query.return_value = {"Items": [{"data": [{"a": 1}]}]}
        response = client.get("/leagues/123/query?platform=SLEEPER&queryType=MATCHUPS")
        assert response.status_code == 200
        assert response.headers["cache-control"] == "private, max-age=300"


class TestFeatureFlagsEndpoint:
    """GET /feature-flags is public (no auth) and returns the global flag map."""

    def test_returns_resolved_flag_map(self, client):
        from common import feature_flags

        feature_flags._override_for_testing({"banner": True})
        response = client.get("/feature-flags")
        assert response.status_code == 200
        body = response.json()
        assert body["detail"] == "Feature flags"
        assert body["data"] == {"banner": True}
        assert response.headers["Cache-Control"] == "no-store"

    def test_defaults_off_when_unset(self, client):
        from common import feature_flags

        feature_flags._override_for_testing({})
        response = client.get("/feature-flags")
        assert response.json()["data"] == {"banner": False}


class TestParseCorsOrigins:
    """CORS allow-list parsing must fail closed and exclude the dev origin in prod."""

    def test_dev_value_allows_localhost_and_prod(self):
        import main

        assert main._parse_cors_origins(
            "http://localhost:5173,https://leagueql.com"
        ) == ["http://localhost:5173", "https://leagueql.com"]

    def test_prod_value_excludes_localhost(self):
        import main

        assert main._parse_cors_origins("https://leagueql.com") == [
            "https://leagueql.com"
        ]
        assert "http://localhost:5173" not in main._parse_cors_origins(
            "https://leagueql.com"
        )

    @pytest.mark.parametrize("raw", ["", "   ", ",", " , "])
    def test_unset_or_empty_fails_closed_to_prod_only(self, raw):
        import main

        # A missing/blank env var must never trust the local dev origin.
        assert main._parse_cors_origins(raw) == ["https://leagueql.com"]

    def test_strips_whitespace_and_blanks(self):
        import main

        assert main._parse_cors_origins(
            " http://localhost:5173 , , https://leagueql.com "
        ) == ["http://localhost:5173", "https://leagueql.com"]


class TestGetLeagueEndpoint:
    def test_returns_league_data(
        self, client, mock_table, league_lookup_item, league_metadata_item
    ):
        mock_table.get_item.side_effect = [
            {"Item": league_lookup_item},
            {"Item": league_metadata_item},
        ]
        mock_table.query.return_value = {
            "Items": [
                {"seasons": {"2023", "2024"}, "canonical_league_id": "canonical-abc"}
            ]
        }
        response = client.get("/leagues/123?platform=SLEEPER")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["league_name"] == "Test League"
        assert "2023" in data["seasons"]
        assert "2024" in data["seasons"]

    def test_returns_refresh_and_onboard_timestamps(
        self, client, mock_table, league_lookup_item, league_metadata_item
    ):
        # The frontend derives data freshness from these fields to drive the
        # stale-league refresh reminder (frontend/refresh-reminder-banner).
        league_metadata_item["onboarded_at"] = "2025-01-15T12:00:00+00:00"
        league_metadata_item["last_refresh_at"] = "2025-08-24T12:00:00+00:00"
        mock_table.get_item.side_effect = [
            {"Item": league_lookup_item},
            {"Item": league_metadata_item},
        ]
        mock_table.query.return_value = {
            "Items": [{"seasons": {"2024"}, "canonical_league_id": "canonical-abc"}]
        }
        response = client.get("/leagues/123?platform=SLEEPER")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["onboarded_at"] == "2025-01-15T12:00:00+00:00"
        assert data["last_refresh_at"] == "2025-08-24T12:00:00+00:00"

    def test_last_refresh_at_null_when_never_refreshed(
        self, client, mock_table, league_lookup_item, league_metadata_item
    ):
        # last_refresh_at is written only on REFRESH, so a never-refreshed league
        # returns null for it while onboarded_at is always present.
        league_metadata_item["onboarded_at"] = "2025-01-15T12:00:00+00:00"
        league_metadata_item.pop("last_refresh_at", None)
        mock_table.get_item.side_effect = [
            {"Item": league_lookup_item},
            {"Item": league_metadata_item},
        ]
        mock_table.query.return_value = {
            "Items": [{"seasons": {"2024"}, "canonical_league_id": "canonical-abc"}]
        }
        response = client.get("/leagues/123?platform=SLEEPER")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["last_refresh_at"] is None
        assert data["onboarded_at"] == "2025-01-15T12:00:00+00:00"

    def test_returns_404_for_unknown_league(self, client, mock_table):
        mock_table.get_item.return_value = {}
        response = client.get("/leagues/999?platform=SLEEPER")
        assert response.status_code == 404

    def test_invalid_league_id_format(self, client):
        response = client.get("/leagues/abc?platform=SLEEPER")
        assert response.status_code == 422

    def test_invalid_platform(self, client):
        response = client.get("/leagues/123?platform=YAHOO")
        assert response.status_code == 422

    def test_cache_control_header(
        self, client, mock_table, league_lookup_item, league_metadata_item
    ):
        mock_table.get_item.side_effect = [
            {"Item": league_lookup_item},
            {"Item": league_metadata_item},
        ]
        mock_table.query.return_value = {
            "Items": [{"seasons": {"2023"}, "canonical_league_id": "canonical-abc"}]
        }
        response = client.get("/leagues/123?platform=SLEEPER")
        assert response.headers["cache-control"] == "no-store"


class TestLeagueAccessTracking:
    """`get_league` records `last_accessed_at` for stale-league detection (backend/league-access-tracking).

    The write is throttled in-memory against the already-fetched METADATA and is
    best-effort — a failed write must never affect the read.
    """

    def _seed_reads(self, mock_table, lookup, metadata):
        mock_table.get_item.side_effect = [{"Item": lookup}, {"Item": metadata}]
        mock_table.query.return_value = {
            "Items": [{"seasons": {"2024"}, "canonical_league_id": "canonical-abc"}]
        }

    def test_writes_when_absent(
        self, client, mock_table, league_lookup_item, league_metadata_item
    ):
        # Default fixture has no last_accessed_at — treated as stale, so a write fires.
        self._seed_reads(mock_table, league_lookup_item, league_metadata_item)
        response = client.get("/leagues/123?platform=SLEEPER")
        assert response.status_code == 200
        mock_table.update_item.assert_called_once()
        kwargs = mock_table.update_item.call_args.kwargs
        assert kwargs["Key"] == {"PK": "LEAGUE#canonical-abc", "SK": "METADATA"}
        assert kwargs["UpdateExpression"] == "SET last_accessed_at = :t"
        assert kwargs["ConditionExpression"] == "attribute_exists(PK)"
        assert isinstance(kwargs["ExpressionAttributeValues"][":t"], str)

    def test_writes_when_stale(
        self, client, mock_table, league_lookup_item, league_metadata_item
    ):
        league_metadata_item["last_accessed_at"] = (
            datetime.now(timezone.utc) - timedelta(hours=2)
        ).isoformat()
        self._seed_reads(mock_table, league_lookup_item, league_metadata_item)
        response = client.get("/leagues/123?platform=SLEEPER")
        assert response.status_code == 200
        mock_table.update_item.assert_called_once()

    def test_skips_when_fresh(
        self, client, mock_table, league_lookup_item, league_metadata_item
    ):
        league_metadata_item["last_accessed_at"] = (
            datetime.now(timezone.utc) - timedelta(minutes=1)
        ).isoformat()
        self._seed_reads(mock_table, league_lookup_item, league_metadata_item)
        response = client.get("/leagues/123?platform=SLEEPER")
        assert response.status_code == 200
        mock_table.update_item.assert_not_called()

    def test_writes_when_stored_value_unparseable(
        self, client, mock_table, league_lookup_item, league_metadata_item
    ):
        league_metadata_item["last_accessed_at"] = "not-a-timestamp"
        self._seed_reads(mock_table, league_lookup_item, league_metadata_item)
        response = client.get("/leagues/123?platform=SLEEPER")
        assert response.status_code == 200
        mock_table.update_item.assert_called_once()

    def test_write_failure_is_swallowed(
        self, client, mock_table, league_lookup_item, league_metadata_item
    ):
        # A concurrent delete (conditional-check failure) or any DynamoDB error on
        # the tracking write must not break the league read.
        self._seed_reads(mock_table, league_lookup_item, league_metadata_item)
        mock_table.update_item.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "ConditionalCheckFailedException"}}, "UpdateItem"
        )
        response = client.get("/leagues/123?platform=SLEEPER")
        assert response.status_code == 200
        assert response.json()["data"]["league_name"] == "Test League"


_JOB_ID = "f47ac10b-58cc-4372-a567-0e02b2c3d479"


class TestGetJobEndpoint:
    def test_returns_in_progress_status(self, client, mock_table):
        mock_table.get_item.return_value = {
            "Item": {
                "PK": f"JOB#{_JOB_ID}",
                "SK": "JOB_STATUS",
                "status": "IN_PROGRESS",
            }
        }
        response = client.get(f"/jobs/{_JOB_ID}")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["status"] == "IN_PROGRESS"
        assert data["failure_reason"] is None

    def test_returns_failure_reason_when_failed(self, client, mock_table):
        mock_table.get_item.return_value = {
            "Item": {
                "PK": f"JOB#{_JOB_ID}",
                "SK": "JOB_STATUS",
                "status": "FAILED",
                "failure_code": "ESPN_AUTH",
                "failure_reason": "ESPN rejected your credentials.",
            }
        }
        response = client.get(f"/jobs/{_JOB_ID}")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["status"] == "FAILED"
        assert data["failure_code"] == "ESPN_AUTH"
        assert data["failure_reason"] == "ESPN rejected your credentials."

    def test_missing_job_reports_failed(self, client, mock_table):
        mock_table.get_item.return_value = {}
        response = client.get(f"/jobs/{_JOB_ID}")
        assert response.status_code == 200
        assert response.json()["data"]["status"] == "FAILED"

    def test_invalid_job_id_rejected(self, client):
        response = client.get("/jobs/not-a-valid-uuid")
        assert response.status_code == 422


class TestFormatCooldownWait:
    @pytest.mark.parametrize(
        "remaining, expected",
        [
            (timedelta(days=7), "7 days"),
            (timedelta(days=5), "5 days"),
            (timedelta(days=1), "1 day"),
            # Partial days round up so the wait is never understated.
            (timedelta(days=4, hours=6), "5 days"),
            (timedelta(days=1, seconds=1), "2 days"),
            # Under a day falls back to whole hours (minimum "1 hour").
            (timedelta(hours=12), "12 hours"),
            (timedelta(hours=1), "1 hour"),
            (timedelta(minutes=30), "1 hour"),
            (timedelta(seconds=0), "1 hour"),
        ],
    )
    def test_format_cooldown_wait(self, remaining, expected):
        import routes

        assert routes._format_cooldown_wait(remaining) == expected


class TestOnboardLeagueEndpoint:
    def test_onboard_new_league(self, client, mock_table, mock_lambda_client):
        mock_table.get_item.return_value = {}
        mock_lambda_client.invoke.return_value = {}
        response = client.post(
            "/leagues",
            json={"leagueId": "123", "platform": "SLEEPER", "season": "2024"},
        )
        assert response.status_code == 201
        assert "onboarding" in response.json()["detail"].lower()
        mock_lambda_client.invoke.assert_called_once()

    def test_returns_200_when_already_onboarded(
        self, client, mock_table, league_lookup_item
    ):
        mock_table.get_item.return_value = {"Item": league_lookup_item}
        response = client.post(
            "/leagues",
            json={"leagueId": "123", "platform": "SLEEPER"},
        )
        assert response.status_code == 200
        assert "already onboarded" in response.json()["detail"].lower()

    def test_refresh_existing_league(
        self,
        client,
        mock_table,
        mock_lambda_client,
        league_lookup_item,
        league_metadata_item,
    ):
        mock_table.get_item.side_effect = [
            {"Item": league_lookup_item},
            {"Item": league_metadata_item},
        ]
        mock_lambda_client.invoke.return_value = {}
        response = client.post(
            "/leagues?requestType=REFRESH",
            json={"leagueId": "123", "platform": "SLEEPER"},
        )
        assert response.status_code == 201
        assert "refresh" in response.json()["detail"].lower()

    def test_refresh_returns_409_when_job_in_progress(
        self, client, mock_table, league_lookup_item, league_metadata_item
    ):
        # An active_job_id pointing at an IN_PROGRESS JOB_STATUS blocks a refresh.
        league_metadata_item["active_job_id"] = _JOB_ID
        mock_table.get_item.side_effect = [
            {"Item": league_lookup_item},
            {"Item": league_metadata_item},
            {"Item": {"status": "IN_PROGRESS"}},
        ]
        response = client.post(
            "/leagues?requestType=REFRESH",
            json={"leagueId": "123", "platform": "SLEEPER"},
        )
        assert response.status_code == 409
        assert "in progress" in response.json()["detail"].lower()

    def test_refresh_proceeds_when_active_job_terminal(
        self,
        client,
        mock_table,
        mock_lambda_client,
        league_lookup_item,
        league_metadata_item,
    ):
        # A completed/expired job must not block a new refresh.
        league_metadata_item["active_job_id"] = _JOB_ID
        mock_table.get_item.side_effect = [
            {"Item": league_lookup_item},
            {"Item": league_metadata_item},
            {"Item": {"status": "COMPLETED"}},
        ]
        mock_lambda_client.invoke.return_value = {}
        response = client.post(
            "/leagues?requestType=REFRESH",
            json={"leagueId": "123", "platform": "SLEEPER"},
        )
        assert response.status_code == 201

    def test_onboard_creates_job_status_item(
        self, client, mock_table, mock_lambda_client
    ):
        mock_table.get_item.return_value = {}
        mock_lambda_client.invoke.return_value = {}
        response = client.post(
            "/leagues",
            json={"leagueId": "123", "platform": "SLEEPER", "season": "2024"},
        )
        assert response.status_code == 201
        job_puts = [
            c
            for c in mock_table.put_item.call_args_list
            if c.kwargs["Item"]["PK"].startswith("JOB#")
        ]
        assert len(job_puts) == 1
        item = job_puts[0].kwargs["Item"]
        assert item["status"] == "IN_PROGRESS"
        assert item["request_type"] == "ONBOARD"
        assert "ttl" in item

    def test_refresh_sets_active_job_pointer(
        self,
        client,
        mock_table,
        mock_lambda_client,
        league_lookup_item,
        league_metadata_item,
    ):
        mock_table.get_item.side_effect = [
            {"Item": league_lookup_item},
            {"Item": league_metadata_item},
        ]
        mock_lambda_client.invoke.return_value = {}
        response = client.post(
            "/leagues?requestType=REFRESH",
            json={"leagueId": "123", "platform": "SLEEPER"},
        )
        assert response.status_code == 201
        active_updates = [
            c
            for c in mock_table.update_item.call_args_list
            if "active_job_id" in c.kwargs.get("UpdateExpression", "")
        ]
        assert active_updates

    def test_refresh_returns_429_when_within_cooldown(
        self, client, mock_table, league_lookup_item, league_metadata_item
    ):
        from datetime import datetime, timedelta, timezone

        recent_time = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        league_metadata_item["last_refresh_at"] = recent_time
        mock_table.get_item.side_effect = [
            {"Item": league_lookup_item},
            {"Item": league_metadata_item},
        ]
        response = client.post(
            "/leagues?requestType=REFRESH",
            json={"leagueId": "123", "platform": "SLEEPER"},
        )
        assert response.status_code == 429
        assert "once per week" in response.json()["detail"]

    def test_refresh_proceeds_when_outside_cooldown(
        self,
        client,
        mock_table,
        mock_lambda_client,
        league_lookup_item,
        league_metadata_item,
    ):
        from datetime import datetime, timedelta, timezone

        old_time = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
        league_metadata_item["last_refresh_at"] = old_time
        mock_table.get_item.side_effect = [
            {"Item": league_lookup_item},
            {"Item": league_metadata_item},
        ]
        mock_lambda_client.invoke.return_value = {}
        response = client.post(
            "/leagues?requestType=REFRESH",
            json={"leagueId": "123", "platform": "SLEEPER"},
        )
        assert response.status_code == 201

    def test_refresh_blocked_when_stored_equals_current_state(
        self, client, mock_table, league_lookup_item, league_metadata_item
    ):
        mock_table.get_item.side_effect = [
            {"Item": league_lookup_item},
            {"Item": league_metadata_item},
        ]
        # Default state is 2025 week 10; stored matchup is also 2025 week 10.
        mock_table.query.return_value = {"Items": [{"SK": "MATCHUPS#2025#WEEK#10"}]}
        response = client.post(
            "/leagues?requestType=REFRESH",
            json={"leagueId": "123", "platform": "SLEEPER"},
        )
        assert response.status_code == 409
        assert "up to date" in response.json()["detail"].lower()

    def test_refresh_blocked_when_stored_ahead_of_state(
        self, client, mock_table, league_lookup_item, league_metadata_item
    ):
        mock_table.get_item.side_effect = [
            {"Item": league_lookup_item},
            {"Item": league_metadata_item},
        ]
        mock_table.query.return_value = {"Items": [{"SK": "MATCHUPS#2025#WEEK#11"}]}
        response = client.post(
            "/leagues?requestType=REFRESH",
            json={"leagueId": "123", "platform": "SLEEPER"},
        )
        assert response.status_code == 409
        assert "up to date" in response.json()["detail"].lower()

    def test_refresh_blocked_during_offseason(
        self,
        client,
        mock_table,
        default_nfl_state,
        league_lookup_item,
        league_metadata_item,
    ):
        mock_table.get_item.side_effect = [
            {"Item": league_lookup_item},
            {"Item": league_metadata_item},
        ]
        default_nfl_state.return_value.json.return_value = {"season_type": "off"}
        response = client.post(
            "/leagues?requestType=REFRESH",
            json={"leagueId": "123", "platform": "SLEEPER"},
        )
        assert response.status_code == 409
        assert "offseason" in response.json()["detail"].lower()

    def test_refresh_allowed_when_no_matchups_stored(
        self,
        client,
        mock_table,
        mock_lambda_client,
        league_lookup_item,
        league_metadata_item,
    ):
        mock_table.get_item.side_effect = [
            {"Item": league_lookup_item},
            {"Item": league_metadata_item},
        ]
        mock_table.query.return_value = {"Items": []}
        mock_lambda_client.invoke.return_value = {}
        response = client.post(
            "/leagues?requestType=REFRESH",
            json={"leagueId": "123", "platform": "SLEEPER"},
        )
        assert response.status_code == 201
        mock_lambda_client.invoke.assert_called_once()

    def test_refresh_fail_open_when_state_api_down(
        self,
        client,
        mock_table,
        mock_lambda_client,
        default_nfl_state,
        league_lookup_item,
        league_metadata_item,
    ):
        mock_table.get_item.side_effect = [
            {"Item": league_lookup_item},
            {"Item": league_metadata_item},
        ]
        default_nfl_state.side_effect = Exception("state API down")
        # Stored matchup is at/ahead of any plausible state, but the guard is
        # skipped because the state fetch fails, so the refresh still proceeds.
        mock_table.query.return_value = {"Items": [{"SK": "MATCHUPS#2099#WEEK#18"}]}
        mock_lambda_client.invoke.return_value = {}
        response = client.post(
            "/leagues?requestType=REFRESH",
            json={"leagueId": "123", "platform": "SLEEPER"},
        )
        assert response.status_code == 201
        mock_lambda_client.invoke.assert_called_once()

    def test_refresh_nonexistent_espn_league_returns_404(self, client, mock_table):
        mock_table.get_item.return_value = {}
        response = client.post(
            "/leagues?requestType=REFRESH",
            json={"leagueId": "123", "platform": "ESPN"},
        )
        assert response.status_code == 404

    def test_refresh_nonexistent_sleeper_league_triggers_lambda(
        self, client, mock_table, mock_lambda_client
    ):
        mock_table.get_item.return_value = {}
        mock_lambda_client.invoke.return_value = {}
        response = client.post(
            "/leagues?requestType=REFRESH",
            json={"leagueId": "123", "platform": "SLEEPER"},
        )
        assert response.status_code == 201
        mock_lambda_client.invoke.assert_called_once()

    def test_returns_500_on_lambda_error(self, client, mock_table, mock_lambda_client):
        mock_table.get_item.return_value = {}
        mock_lambda_client.invoke.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "ServiceError", "Message": "fail"}}, "Invoke"
        )
        response = client.post(
            "/leagues",
            json={"leagueId": "123", "platform": "SLEEPER"},
        )
        assert response.status_code == 500

    def test_invalid_platform_returns_500(self, client, mock_table):
        # platform is a plain str in OnboardingPayload; Platform() conversion
        # happens in the handler body, so an invalid value raises ValueError -> 500
        mock_table.get_item.return_value = {}
        response = client.post(
            "/leagues",
            json={"leagueId": "123", "platform": "YAHOO"},
        )
        assert response.status_code == 500

    def test_payload_league_id_too_long_returns_422(self, client):
        response = client.post(
            "/leagues",
            json={"leagueId": "123", "platform": "SLEEPER", "season": "x" * 101},
        )
        assert response.status_code == 422

    def test_non_404_lookup_error_is_reraised(self, client, mock_table):
        import botocore.exceptions

        mock_table.get_item.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "InternalError", "Message": "server error"}}, "GetItem"
        )
        response = client.post(
            "/leagues",
            json={"leagueId": "123", "platform": "SLEEPER"},
        )
        assert response.status_code == 500


class TestDeleteLeagueEndpoint:
    def _setup_delete_mocks(self, mock_table, league_lookup_item, mock_s3_client):
        mock_table.get_item.return_value = {"Item": league_lookup_item}
        mock_table.delete_item.return_value = {}
        mock_writer = MagicMock()
        mock_table.batch_writer.return_value.__enter__ = MagicMock(
            return_value=mock_writer
        )
        mock_table.batch_writer.return_value.__exit__ = MagicMock(return_value=False)
        mock_table.query.return_value = {"Items": []}
        mock_s3_client.list_objects_v2.return_value = {}
        return mock_writer

    def test_deletes_league_successfully(
        self, client, mock_table, mock_s3_client, league_lookup_item
    ):
        self._setup_delete_mocks(mock_table, league_lookup_item, mock_s3_client)
        response = client.delete("/leagues/123?platform=SLEEPER")
        assert response.status_code == 200
        assert "deleted" in response.json()["detail"].lower()

    def test_deletes_s3_objects_when_present(
        self, client, mock_table, mock_s3_client, league_lookup_item
    ):
        self._setup_delete_mocks(mock_table, league_lookup_item, mock_s3_client)
        mock_s3_client.list_objects_v2.return_value = {
            "Contents": [{"Key": "raw-api-data/canonical-abc/file.json"}]
        }
        response = client.delete("/leagues/123?platform=SLEEPER")
        assert response.status_code == 200
        mock_s3_client.delete_objects.assert_called_once()

    def test_skips_s3_delete_when_no_objects(
        self, client, mock_table, mock_s3_client, league_lookup_item
    ):
        self._setup_delete_mocks(mock_table, league_lookup_item, mock_s3_client)
        response = client.delete("/leagues/123?platform=SLEEPER")
        assert response.status_code == 200
        mock_s3_client.delete_objects.assert_not_called()

    def test_returns_404_for_unknown_league(self, client, mock_table):
        mock_table.get_item.return_value = {}
        response = client.delete("/leagues/999?platform=SLEEPER")
        assert response.status_code == 404

    def test_deletes_gsi_lookup_items(
        self, client, mock_table, mock_s3_client, league_lookup_item, mock_time_sleep
    ):
        mock_table.get_item.return_value = {"Item": league_lookup_item}
        mock_table.delete_item.return_value = {}
        mock_writer = MagicMock()
        mock_table.batch_writer.return_value.__enter__ = MagicMock(
            return_value=mock_writer
        )
        mock_table.batch_writer.return_value.__exit__ = MagicMock(return_value=False)
        mock_table.query.side_effect = [
            {"Items": [{"PK": "LEAGUE#123#PLATFORM#SLEEPER", "SK": "LEAGUE_LOOKUP"}]},
            {"Items": []},
            {"Items": []},
            {"Items": []},
            {"Items": []},
            {"Items": []},
            {"Items": []},
            {"Items": []},
        ]
        mock_s3_client.list_objects_v2.return_value = {}
        response = client.delete("/leagues/123?platform=SLEEPER")
        assert response.status_code == 200
        mock_writer.delete_item.assert_any_call(
            Key={"PK": "LEAGUE#123#PLATFORM#SLEEPER", "SK": "LEAGUE_LOOKUP"}
        )

    def test_paginated_gsi_query_during_delete(
        self, client, mock_table, mock_s3_client, league_lookup_item, mock_time_sleep
    ):
        mock_table.get_item.return_value = {"Item": league_lookup_item}
        mock_table.delete_item.return_value = {}
        mock_writer = MagicMock()
        mock_table.batch_writer.return_value.__enter__ = MagicMock(
            return_value=mock_writer
        )
        mock_table.batch_writer.return_value.__exit__ = MagicMock(return_value=False)
        mock_table.query.side_effect = [
            {
                "Items": [{"PK": "LEAGUE#123#PLATFORM#SLEEPER", "SK": "LEAGUE_LOOKUP"}],
                "LastEvaluatedKey": {
                    "PK": "LEAGUE#123#PLATFORM#SLEEPER",
                    "SK": "LEAGUE_LOOKUP",
                },
            },
            {"Items": []},
            {"Items": []},
            {"Items": []},
            {"Items": []},
            {"Items": []},
            {"Items": []},
            {"Items": []},
        ]
        mock_s3_client.list_objects_v2.return_value = {}
        response = client.delete("/leagues/123?platform=SLEEPER")
        assert response.status_code == 200
        # Pass 1 paginates the canonical-PK query (2 calls) + GSI1 (1 call);
        # pass 2 verifies clean (PK + GSI1 = 2 calls).
        assert mock_table.query.call_count == 5

    def test_decrements_league_count_on_successful_delete(
        self, client, mock_table, mock_s3_client, league_lookup_item
    ):
        from decimal import Decimal

        self._setup_delete_mocks(mock_table, league_lookup_item, mock_s3_client)
        response = client.delete("/leagues/123?platform=SLEEPER")
        assert response.status_code == 200
        mock_table.update_item.assert_called_once_with(
            Key={"PK": "APP#STATS", "SK": "LEAGUE_COUNT"},
            UpdateExpression="ADD league_count :delta",
            ExpressionAttributeValues={":delta": Decimal(-1)},
        )

    def test_client_error_during_delete_returns_500(
        self, client, mock_table, league_lookup_item
    ):
        import botocore.exceptions

        mock_table.get_item.return_value = {"Item": league_lookup_item}
        mock_table.query.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "InternalError", "Message": "fail"}}, "Query"
        )
        response = client.delete("/leagues/123?platform=SLEEPER")
        assert response.status_code == 500

    def test_orphaned_items_fail_and_skip_count_update(
        self, client, mock_table, league_lookup_item, mock_s3_client, mock_time_sleep
    ):
        mock_table.get_item.return_value = {"Item": league_lookup_item}
        mock_writer = MagicMock()
        mock_table.batch_writer.return_value.__enter__ = MagicMock(
            return_value=mock_writer
        )
        mock_table.batch_writer.return_value.__exit__ = MagicMock(return_value=False)
        # Items never clear, so every verify pass still finds them.
        mock_table.query.return_value = {
            "Items": [{"PK": "LEAGUE#canonical-abc", "SK": "TEAMS#2024"}]
        }
        response = client.delete("/leagues/123?platform=SLEEPER")
        assert response.status_code == 500
        assert "fully delete" in response.json()["detail"].lower()
        # League count must not be decremented when the delete is incomplete.
        mock_table.update_item.assert_not_called()
        mock_s3_client.delete_objects.assert_not_called()


class TestQueryLeagueEndpoint:
    def test_query_with_suffix_returns_item(
        self, client, mock_table, league_lookup_item, league_metadata_item
    ):
        mock_table.get_item.side_effect = [
            {"Item": league_lookup_item},
            {"Item": league_metadata_item},
            {
                "Item": {
                    "PK": "LEAGUE#canonical-abc",
                    "SK": "MATCHUPS#2024",
                    "data": [{"week": 1}],
                }
            },
        ]
        response = client.get(
            "/leagues/123/query?platform=SLEEPER&queryType=MATCHUPS%232024"
        )
        assert response.status_code == 200
        assert response.json()["data"] == [{"week": 1}]

    def test_query_without_suffix_returns_all_items(
        self, client, mock_table, league_lookup_item
    ):
        mock_table.get_item.return_value = {"Item": league_lookup_item}
        mock_table.query.return_value = {
            "Items": [
                {"data": [{"week": 1}]},
                {"data": [{"week": 2}]},
            ]
        }
        response = client.get("/leagues/123/query?platform=SLEEPER&queryType=MATCHUPS")
        assert response.status_code == 200
        assert response.json()["data"] == [{"week": 1}, {"week": 2}]

    def test_query_handles_pagination(self, client, mock_table, league_lookup_item):
        mock_table.get_item.return_value = {"Item": league_lookup_item}
        mock_table.query.side_effect = [
            {
                "Items": [{"data": [{"week": 1}]}],
                "LastEvaluatedKey": {"PK": "x", "SK": "y"},
            },
            {"Items": [{"data": [{"week": 2}]}]},
        ]
        response = client.get("/leagues/123/query?platform=SLEEPER&queryType=MATCHUPS")
        assert response.status_code == 200
        assert len(response.json()["data"]) == 2

    def test_query_converts_decimals(
        self, client, mock_table, league_lookup_item, sample_matchup_items
    ):
        mock_table.get_item.return_value = {"Item": league_lookup_item}
        mock_table.query.return_value = {"Items": sample_matchup_items}
        response = client.get("/leagues/123/query?platform=SLEEPER&queryType=MATCHUPS")
        assert response.status_code == 200
        row = response.json()["data"][0]
        assert isinstance(row["home_score"], float)
        assert row["home_score"] == 120.5

    def test_query_returns_404_when_no_data(
        self, client, mock_table, league_lookup_item
    ):
        mock_table.get_item.return_value = {"Item": league_lookup_item}
        mock_table.query.return_value = {"Items": []}
        response = client.get("/leagues/123/query?platform=SLEEPER&queryType=MATCHUPS")
        assert response.status_code == 404

    def test_query_returns_404_when_item_missing(
        self, client, mock_table, league_lookup_item, league_metadata_item
    ):
        mock_table.get_item.side_effect = [
            {"Item": league_lookup_item},
            {"Item": league_metadata_item},
            {},
        ]
        response = client.get(
            "/leagues/123/query?platform=SLEEPER&queryType=MATCHUPS%232024"
        )
        assert response.status_code == 404

    def test_invalid_query_type_returns_400(
        self, client, mock_table, league_lookup_item
    ):
        mock_table.get_item.return_value = {"Item": league_lookup_item}
        response = client.get(
            "/leagues/123/query?platform=SLEEPER&queryType=INVALID_TYPE"
        )
        assert response.status_code == 400

    def test_cache_control_header_set(self, client, mock_table, league_lookup_item):
        mock_table.get_item.return_value = {"Item": league_lookup_item}
        mock_table.query.return_value = {"Items": [{"data": [{"week": 1}]}]}
        response = client.get("/leagues/123/query?platform=SLEEPER&queryType=MATCHUPS")
        assert response.headers["cache-control"] == "private, max-age=300"

    def test_boto_error_returns_500(
        self, client, mock_table, league_lookup_item, league_metadata_item
    ):
        mock_table.get_item.side_effect = [
            {"Item": league_lookup_item},
            {"Item": league_metadata_item},
            botocore.exceptions.ClientError(
                {"Error": {"Code": "InternalError", "Message": "fail"}}, "GetItem"
            ),
        ]
        response = client.get(
            "/leagues/123/query?platform=SLEEPER&queryType=MATCHUPS%232024"
        )
        assert response.status_code == 500

    @pytest.mark.parametrize(
        "query_type,sk_base",
        [
            ("TEAMS", "TEAMS"),
            ("MATCHUPS", "MATCHUPS"),
            ("SEASON_STANDINGS", "STANDINGS"),
            ("WEEKLY_STANDINGS", "WEEKLY_STANDINGS"),
            ("PLAYOFF_BRACKET", "PLAYOFF_BRACKET"),
            ("DRAFT", "DRAFT"),
        ],
    )
    def test_query_type_to_sk_base_mapping(
        self, client, mock_table, league_lookup_item, query_type, sk_base
    ):
        from boto3.dynamodb.conditions import ConditionExpressionBuilder

        mock_table.get_item.return_value = {"Item": league_lookup_item}
        mock_table.query.return_value = {"Items": [{"data": []}]}
        client.get(f"/leagues/123/query?platform=SLEEPER&queryType={query_type}")
        call_kwargs = mock_table.query.call_args[1]
        condition = call_kwargs["KeyConditionExpression"]
        rendered = ConditionExpressionBuilder().build_expression(condition)
        sk_values = list(rendered.attribute_value_placeholders.values())
        assert any(str(v).startswith(sk_base) for v in sk_values)

    def test_transactions_suffixed_query_uses_prefix_scan(
        self, client, mock_table, league_lookup_item, league_metadata_item
    ):
        # Transactions are stored across chunk items, so a season-suffixed query resolves
        # via a begins_with prefix query (not an exact get_item) and concatenates chunks.
        from boto3.dynamodb.conditions import ConditionExpressionBuilder

        mock_table.get_item.side_effect = [
            {"Item": league_lookup_item},
            {"Item": league_metadata_item},
        ]
        mock_table.query.return_value = {
            "Items": [
                {"SK": "TRANSACTIONS#2024#0000", "data": [{"transaction_id": "a"}]},
                {"SK": "TRANSACTIONS#2024#0001", "data": [{"transaction_id": "b"}]},
            ]
        }
        response = client.get(
            "/leagues/123/query?platform=SLEEPER&queryType=TRANSACTIONS%232024"
        )
        assert response.status_code == 200
        assert response.json()["data"] == [
            {"transaction_id": "a"},
            {"transaction_id": "b"},
        ]
        # The view read used query/begins_with; get_item was only lookup + metadata.
        mock_table.query.assert_called_once()
        assert mock_table.get_item.call_count == 2
        # The prefix has no trailing "#", so it matches both chunk and legacy keys.
        condition = mock_table.query.call_args[1]["KeyConditionExpression"]
        rendered = ConditionExpressionBuilder().build_expression(condition)
        sk_values = list(rendered.attribute_value_placeholders.values())
        assert "TRANSACTIONS#2024" in sk_values

    def test_standings_suffixed_query_still_uses_get_item(
        self, client, mock_table, league_lookup_item, league_metadata_item
    ):
        # A non-chunked suffixed view is unchanged: exact get_item, no prefix query.
        mock_table.get_item.side_effect = [
            {"Item": league_lookup_item},
            {"Item": league_metadata_item},
            {"Item": {"SK": "STANDINGS#2024", "data": [{"rank": 1}]}},
        ]
        response = client.get(
            "/leagues/123/query?platform=SLEEPER&queryType=SEASON_STANDINGS%232024"
        )
        assert response.status_code == 200
        assert response.json()["data"] == [{"rank": 1}]
        mock_table.query.assert_not_called()
        assert mock_table.get_item.call_count == 3  # lookup, metadata, view

    def test_transactions_query_concatenates_chunks_across_pages(
        self, client, mock_table, league_lookup_item, league_metadata_item
    ):
        mock_table.get_item.side_effect = [
            {"Item": league_lookup_item},
            {"Item": league_metadata_item},
        ]
        mock_table.query.side_effect = [
            {
                "Items": [
                    {"SK": "TRANSACTIONS#2024#0000", "data": [{"id": 1}, {"id": 2}]}
                ],
                "LastEvaluatedKey": {"PK": "x", "SK": "y"},
            },
            {"Items": [{"SK": "TRANSACTIONS#2024#0001", "data": [{"id": 3}]}]},
        ]
        response = client.get(
            "/leagues/123/query?platform=SLEEPER&queryType=TRANSACTIONS%232024"
        )
        assert response.status_code == 200
        assert response.json()["data"] == [{"id": 1}, {"id": 2}, {"id": 3}]
        assert mock_table.query.call_count == 2

    def test_transactions_query_reads_legacy_bare_item(
        self, client, mock_table, league_lookup_item, league_metadata_item
    ):
        # A league onboarded before chunking has a single bare TRANSACTIONS#{season}
        # item, which the backward-compatible prefix query still matches.
        mock_table.get_item.side_effect = [
            {"Item": league_lookup_item},
            {"Item": league_metadata_item},
        ]
        mock_table.query.return_value = {
            "Items": [{"SK": "TRANSACTIONS#2024", "data": [{"id": 1}]}]
        }
        response = client.get(
            "/leagues/123/query?platform=SLEEPER&queryType=TRANSACTIONS%232024"
        )
        assert response.status_code == 200
        assert response.json()["data"] == [{"id": 1}]

    def test_transactions_query_returns_404_when_no_items(
        self, client, mock_table, league_lookup_item, league_metadata_item
    ):
        mock_table.get_item.side_effect = [
            {"Item": league_lookup_item},
            {"Item": league_metadata_item},
        ]
        mock_table.query.return_value = {"Items": []}
        response = client.get(
            "/leagues/123/query?platform=SLEEPER&queryType=TRANSACTIONS%232024"
        )
        assert response.status_code == 404


_VALID_MAPPING_ENTRY = {
    "currentPlatformOwnerId": "espn-owner-1",
    "newPlatformOwnerId": "sleeper-owner-1",
    "displayName": "Manager One",
}


class TestMigrateLeagueEndpoint:
    # Successful migration: get_item calls are (1) current league lookup,
    # (2) metadata fetch, (3) new platform league lookup (returns {} → 404).
    _PAYLOAD: ClassVar = {
        "newPlatformLeagueId": "456",
        "newPlatform": "SLEEPER",
        "season": "2025",
        "managerMapping": [],
    }

    def _setup_success_mocks(
        self, mock_table, mock_lambda_client, league_lookup_item, league_metadata_item
    ):
        mock_table.get_item.side_effect = [
            {"Item": league_lookup_item},
            {"Item": league_metadata_item},
            {},
        ]
        mock_table.put_item.return_value = {}
        mock_table.update_item.return_value = {}
        mock_lambda_client.invoke.return_value = {}

    def test_successful_migration_returns_202(
        self,
        client,
        mock_table,
        mock_lambda_client,
        league_lookup_item,
        league_metadata_item,
    ):
        self._setup_success_mocks(
            mock_table, mock_lambda_client, league_lookup_item, league_metadata_item
        )
        response = client.post(
            "/leagues/123/migrate?platform=SLEEPER", json=self._PAYLOAD
        )
        assert response.status_code == 202
        assert "migration started" in response.json()["detail"].lower()
        assert "correlation_id" in response.json()["data"]

    def test_successful_migration_invokes_lambda(
        self,
        client,
        mock_table,
        mock_lambda_client,
        league_lookup_item,
        league_metadata_item,
    ):
        self._setup_success_mocks(
            mock_table, mock_lambda_client, league_lookup_item, league_metadata_item
        )
        client.post("/leagues/123/migrate?platform=SLEEPER", json=self._PAYLOAD)
        mock_lambda_client.invoke.assert_called_once()
        call_payload = mock_lambda_client.invoke.call_args[1]["Payload"]
        import json

        parsed = json.loads(call_payload)
        assert parsed["requestType"] == "MIGRATE"
        assert parsed["body"]["leagueId"] == "456"
        assert parsed["body"]["platform"] == "SLEEPER"

    def test_migration_creates_job_and_active_pointer(
        self,
        client,
        mock_table,
        mock_lambda_client,
        league_lookup_item,
        league_metadata_item,
    ):
        self._setup_success_mocks(
            mock_table, mock_lambda_client, league_lookup_item, league_metadata_item
        )
        response = client.post(
            "/leagues/123/migrate?platform=SLEEPER", json=self._PAYLOAD
        )
        assert response.status_code == 202
        job_puts = [
            c
            for c in mock_table.put_item.call_args_list
            if c.kwargs["Item"]["PK"].startswith("JOB#")
        ]
        assert len(job_puts) == 1
        assert job_puts[0].kwargs["Item"]["request_type"] == "MIGRATE"
        active_updates = [
            c
            for c in mock_table.update_item.call_args_list
            if "active_job_id" in c.kwargs.get("UpdateExpression", "")
        ]
        assert active_updates

    def test_returns_409_when_job_in_progress(
        self,
        client,
        mock_table,
        league_lookup_item,
        league_metadata_item,
    ):
        # An active_job_id pointing at an IN_PROGRESS job blocks a migration.
        league_metadata_item["active_job_id"] = _JOB_ID
        mock_table.get_item.side_effect = [
            {"Item": league_lookup_item},
            {"Item": league_metadata_item},
            {"Item": {"status": "IN_PROGRESS"}},
        ]
        response = client.post(
            "/leagues/123/migrate?platform=SLEEPER", json=self._PAYLOAD
        )
        assert response.status_code == 409
        assert "in progress" in response.json()["detail"].lower()

    def test_returns_409_when_new_platform_league_already_onboarded(
        self,
        client,
        mock_table,
        league_lookup_item,
        league_metadata_item,
    ):
        new_platform_lookup = {
            "PK": "LEAGUE#456#PLATFORM#SLEEPER",
            "SK": "LEAGUE_LOOKUP",
            "canonical_league_id": "canonical-xyz",
        }
        mock_table.get_item.side_effect = [
            {"Item": league_lookup_item},
            {"Item": league_metadata_item},
            {"Item": new_platform_lookup},
        ]
        response = client.post(
            "/leagues/123/migrate?platform=SLEEPER", json=self._PAYLOAD
        )
        assert response.status_code == 409
        assert "already onboarded" in response.json()["detail"].lower()

    def test_returns_404_when_current_league_not_found(self, client, mock_table):
        mock_table.get_item.return_value = {}
        response = client.post(
            "/leagues/999/migrate?platform=SLEEPER", json=self._PAYLOAD
        )
        assert response.status_code == 404

    def test_returns_422_for_invalid_league_id_format(self, client):
        response = client.post(
            "/leagues/abc/migrate?platform=SLEEPER", json=self._PAYLOAD
        )
        assert response.status_code == 422

    def test_returns_422_for_new_platform_league_id_too_long(self, client):
        payload = {**self._PAYLOAD, "newPlatformLeagueId": "x" * 101}
        response = client.post("/leagues/123/migrate?platform=SLEEPER", json=payload)
        assert response.status_code == 422

    @pytest.mark.parametrize(
        "bad_mapping",
        [
            pytest.param(
                [{**_VALID_MAPPING_ENTRY, "extraField": "nope"}], id="unknown_key"
            ),
            pytest.param(
                [{"currentPlatformOwnerId": "x", "newPlatformOwnerId": "y"}],
                id="missing_display_name",
            ),
            pytest.param(
                [{**_VALID_MAPPING_ENTRY, "displayName": 123}],
                id="non_string_value",
            ),
            pytest.param(
                [{**_VALID_MAPPING_ENTRY, "currentPlatformOwnerId": "x" * 101}],
                id="owner_id_too_long",
            ),
            pytest.param(
                [dict(_VALID_MAPPING_ENTRY) for _ in range(65)],
                id="too_many_entries",
            ),
        ],
    )
    def test_returns_422_for_invalid_manager_mapping(self, client, bad_mapping):
        payload = {**self._PAYLOAD, "managerMapping": bad_mapping}
        response = client.post("/leagues/123/migrate?platform=SLEEPER", json=payload)
        assert response.status_code == 422

    def test_invalid_manager_mapping_writes_no_migration_item(self, client, mock_table):
        payload = {
            **self._PAYLOAD,
            "managerMapping": [{**_VALID_MAPPING_ENTRY, "extraField": "nope"}],
        }
        response = client.post("/leagues/123/migrate?platform=SLEEPER", json=payload)
        assert response.status_code == 422
        mock_table.put_item.assert_not_called()

    def test_valid_manager_mapping_stored_as_plain_dicts(
        self,
        client,
        mock_table,
        mock_lambda_client,
        league_lookup_item,
        league_metadata_item,
    ):
        self._setup_success_mocks(
            mock_table, mock_lambda_client, league_lookup_item, league_metadata_item
        )
        payload = {**self._PAYLOAD, "managerMapping": [_VALID_MAPPING_ENTRY]}
        response = client.post("/leagues/123/migrate?platform=SLEEPER", json=payload)
        assert response.status_code == 202
        migration_puts = [
            c
            for c in mock_table.put_item.call_args_list
            if str(c.kwargs["Item"]["SK"]).startswith("PLATFORM_MIGRATION#")
        ]
        assert len(migration_puts) == 1
        assert migration_puts[0].kwargs["Item"]["data"] == [_VALID_MAPPING_ENTRY]

    def test_returns_500_on_dynamodb_error_during_setup(
        self,
        client,
        mock_table,
        league_lookup_item,
        league_metadata_item,
    ):
        mock_table.get_item.side_effect = [
            {"Item": league_lookup_item},
            {"Item": league_metadata_item},
            {},
        ]
        mock_table.put_item.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "InternalError", "Message": "fail"}}, "PutItem"
        )
        response = client.post(
            "/leagues/123/migrate?platform=SLEEPER", json=self._PAYLOAD
        )
        assert response.status_code == 500
        assert "migration" in response.json()["detail"].lower()

    def test_returns_500_on_lambda_invocation_error(
        self,
        client,
        mock_table,
        mock_lambda_client,
        league_lookup_item,
        league_metadata_item,
    ):
        mock_table.get_item.side_effect = [
            {"Item": league_lookup_item},
            {"Item": league_metadata_item},
            {},
        ]
        mock_table.put_item.return_value = {}
        mock_table.update_item.return_value = {}
        mock_lambda_client.invoke.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "ServiceError", "Message": "fail"}}, "Invoke"
        )
        response = client.post(
            "/leagues/123/migrate?platform=SLEEPER", json=self._PAYLOAD
        )
        assert response.status_code == 500
        assert "trigger" in response.json()["detail"].lower()


class TestGetNflState:
    def test_returns_state_on_success(self, default_nfl_state):
        import main

        default_nfl_state.return_value.json.return_value = {
            "season_type": "regular",
            "season": "2025",
            "week": "10",
        }
        result = main.get_nfl_state()
        assert result == {"season_type": "regular", "season": "2025", "week": "10"}
        default_nfl_state.return_value.raise_for_status.assert_called_once()

    def test_returns_none_on_failure(self, default_nfl_state):
        import main

        default_nfl_state.side_effect = Exception("network error")
        assert main.get_nfl_state() is None


class TestGetLatestStoredMatchup:
    def test_parses_latest_season_and_week(self, mock_table):
        import main

        mock_table.query.return_value = {"Items": [{"SK": "MATCHUPS#2025#WEEK#07"}]}
        assert main.get_latest_stored_matchup("canonical-abc") == (2025, 7)

    def test_returns_none_when_no_matchups(self, mock_table):
        import main

        mock_table.query.return_value = {"Items": []}
        assert main.get_latest_stored_matchup("canonical-abc") is None

    def test_raises_500_on_client_error(self, mock_table):
        import main
        from fastapi import HTTPException

        mock_table.query.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "InternalError", "Message": "fail"}}, "Query"
        )
        with pytest.raises(HTTPException) as exc_info:
            main.get_latest_stored_matchup("canonical-abc")
        assert exc_info.value.status_code == 500


class TestEspnMembersEndpoint:
    """The /espn_members endpoint proxies ESPN's API server-side to avoid CORS."""

    _PAYLOAD: ClassVar = {"swid": "{abc}", "s2": "s2-token"}
    _URL = "/leagues/123/espn_members?platform=ESPN&espnLeagueId=99&season=2024"

    def test_returns_members_on_success(self, client, mock_table, league_lookup_item):
        mock_table.get_item.return_value = {"Item": league_lookup_item}
        espn_resp = MagicMock()
        espn_resp.raise_for_status = MagicMock()
        espn_resp.json.return_value = {
            "members": [
                {"id": "m1", "displayName": "Alice"},
                {"id": "m2"},  # no displayName -> falls back to id
            ]
        }
        with patch("main.http_requests.get", return_value=espn_resp):
            response = client.post(self._URL, json=self._PAYLOAD)
        assert response.status_code == 200
        data = response.json()["data"]
        assert {"owner_id": "m1", "display_name": "Alice"} in data
        assert {"owner_id": "m2", "display_name": "m2"} in data

    def test_http_error_returns_502(self, client, mock_table, league_lookup_item):
        import requests

        mock_table.get_item.return_value = {"Item": league_lookup_item}
        espn_resp = MagicMock()
        espn_resp.raise_for_status.side_effect = requests.exceptions.HTTPError("403")
        with patch("main.http_requests.get", return_value=espn_resp):
            response = client.post(self._URL, json=self._PAYLOAD)
        assert response.status_code == 502
        assert "fetch ESPN league members" in response.json()["detail"]

    def test_request_exception_returns_502(
        self, client, mock_table, league_lookup_item
    ):
        import requests

        mock_table.get_item.return_value = {"Item": league_lookup_item}
        with patch(
            "main.http_requests.get",
            side_effect=requests.exceptions.ConnectionError("boom"),
        ):
            response = client.post(self._URL, json=self._PAYLOAD)
        assert response.status_code == 502
        assert "reach ESPN API" in response.json()["detail"]

    def test_parse_error_returns_502(self, client, mock_table, league_lookup_item):
        mock_table.get_item.return_value = {"Item": league_lookup_item}
        espn_resp = MagicMock()
        espn_resp.raise_for_status = MagicMock()
        espn_resp.json.return_value = {"members": [{}]}  # missing "id" -> KeyError
        with patch("main.http_requests.get", return_value=espn_resp):
            response = client.post(self._URL, json=self._PAYLOAD)
        assert response.status_code == 502
        assert "parse ESPN API response" in response.json()["detail"]

    @pytest.mark.parametrize(
        "espn_league_id",
        [
            "99?view=evil",  # query-parameter injection
            "../../../other/path",  # path traversal within the ESPN host
            "99&x=1",  # extra query param
            "abc",  # non-numeric
            "",  # empty
        ],
    )
    def test_invalid_espn_league_id_returns_422_without_upstream_call(
        self, client, mock_table, league_lookup_item, espn_league_id
    ):
        # Injection-shaped espnLeagueId values must be rejected by validation
        # before any ESPN request is made (no path traversal / param injection).
        mock_table.get_item.return_value = {"Item": league_lookup_item}
        from urllib.parse import quote

        url = (
            f"/leagues/123/espn_members?platform=ESPN"
            f"&espnLeagueId={quote(espn_league_id, safe='')}&season=2024"
        )
        with patch("main.http_requests.get") as mock_get:
            response = client.post(url, json=self._PAYLOAD)
        assert response.status_code == 422
        mock_get.assert_not_called()

    @pytest.mark.parametrize("season", ["2024/..", "20x4", "12345", "abcd", ""])
    def test_invalid_season_returns_422_without_upstream_call(
        self, client, mock_table, league_lookup_item, season
    ):
        mock_table.get_item.return_value = {"Item": league_lookup_item}
        from urllib.parse import quote

        url = (
            f"/leagues/123/espn_members?platform=ESPN"
            f"&espnLeagueId=99&season={quote(season, safe='')}"
        )
        with patch("main.http_requests.get") as mock_get:
            response = client.post(url, json=self._PAYLOAD)
        assert response.status_code == 422
        mock_get.assert_not_called()


def _as_user(user_id):
    """Override the Clerk auth dependency to a specific (non-default) caller."""
    import main
    import routes

    main.app.dependency_overrides[routes.get_authenticated_user] = lambda: user_id


class TestOwnerGate:
    """Mutating endpoints are owner-gated (backend/league-authorization): a non-owner gets 403."""

    def test_delete_non_owner_returns_403(self, client, mock_table, league_lookup_item):
        mock_table.get_item.return_value = {"Item": league_lookup_item}
        _as_user("intruder")
        response = client.delete("/leagues/123?platform=SLEEPER")
        assert response.status_code == 403

    def test_migrate_non_owner_returns_403(
        self, client, mock_table, league_lookup_item, league_metadata_item
    ):
        mock_table.get_item.side_effect = [
            {"Item": league_lookup_item},
            {"Item": league_metadata_item},
        ]
        _as_user("intruder")
        response = client.post(
            "/leagues/123/migrate?platform=SLEEPER",
            json={
                "newPlatformLeagueId": "456",
                "newPlatform": "ESPN",
                "season": "2024",
                "managerMapping": [],
            },
        )
        assert response.status_code == 403

    def test_refresh_non_owner_returns_403(
        self, client, mock_table, league_lookup_item, league_metadata_item
    ):
        mock_table.get_item.side_effect = [
            {"Item": league_lookup_item},
            {"Item": league_metadata_item},
        ]
        _as_user("intruder")
        response = client.post(
            "/leagues?requestType=REFRESH",
            json={"leagueId": "123", "platform": "SLEEPER"},
        )
        assert response.status_code == 403

    def test_espn_members_non_owner_returns_403(
        self, client, mock_table, league_lookup_item
    ):
        mock_table.get_item.return_value = {"Item": league_lookup_item}
        _as_user("intruder")
        with patch("main.http_requests.get") as mock_get:
            response = client.post(
                "/leagues/123/espn_members?platform=ESPN&espnLeagueId=99&season=2024",
                json={"swid": "{abc}", "s2": "s2-token"},
            )
        assert response.status_code == 403
        mock_get.assert_not_called()


class TestGetLeagueIsOwner:
    """get_league returns is_owner and member-gates ESPN reads (backend/league-authorization)."""

    def _seasons_query(self, mock_table):
        mock_table.query.return_value = {
            "Items": [{"seasons": {"2024"}, "canonical_league_id": "canonical-abc"}]
        }

    def test_is_owner_true_for_owner(
        self, client, mock_table, league_lookup_item, league_metadata_item
    ):
        mock_table.get_item.side_effect = [
            {"Item": league_lookup_item},
            {"Item": league_metadata_item},
        ]
        self._seasons_query(mock_table)
        response = client.get("/leagues/123?platform=SLEEPER")
        assert response.status_code == 200
        assert response.json()["data"]["is_owner"] is True

    def test_is_owner_false_for_non_owner_sleeper(
        self, client, mock_table, league_lookup_item, league_metadata_item
    ):
        mock_table.get_item.side_effect = [
            {"Item": league_lookup_item},
            {"Item": league_metadata_item},
        ]
        self._seasons_query(mock_table)
        _as_user("user_2")  # not the owner, but Sleeper reads stay open
        response = client.get("/leagues/123?platform=SLEEPER")
        assert response.status_code == 200
        assert response.json()["data"]["is_owner"] is False

    def test_espn_non_member_returns_403(
        self, client, mock_table, league_lookup_item, league_metadata_item
    ):
        mock_table.get_item.side_effect = [
            {"Item": league_lookup_item},
            {"Item": league_metadata_item},
        ]
        _as_user("stranger")
        response = client.get("/leagues/123?platform=ESPN")
        assert response.status_code == 403

    def test_espn_member_allowed(
        self, client, mock_table, league_lookup_item, league_metadata_item
    ):
        league_metadata_item["members"] = {"user_1", "user_2"}
        mock_table.get_item.side_effect = [
            {"Item": league_lookup_item},
            {"Item": league_metadata_item},
        ]
        self._seasons_query(mock_table)
        _as_user("user_2")
        response = client.get("/leagues/123?platform=ESPN")
        assert response.status_code == 200
        assert response.json()["data"]["is_owner"] is False


class TestQueryLeagueMemberGate:
    """query_league member-gates ESPN reads (backend/league-authorization)."""

    def test_espn_non_member_returns_403(
        self, client, mock_table, league_lookup_item, league_metadata_item
    ):
        mock_table.get_item.side_effect = [
            {"Item": league_lookup_item},
            {"Item": league_metadata_item},
        ]
        _as_user("stranger")
        response = client.get("/leagues/123/query?platform=ESPN&queryType=MATCHUPS")
        assert response.status_code == 403

    def test_espn_member_allowed(
        self, client, mock_table, league_lookup_item, league_metadata_item
    ):
        league_metadata_item["members"] = {"user_1", "user_2"}
        mock_table.get_item.side_effect = [
            {"Item": league_lookup_item},
            {"Item": league_metadata_item},
        ]
        mock_table.query.return_value = {"Items": [{"data": [{"week": 1}]}]}
        _as_user("user_2")
        response = client.get("/leagues/123/query?platform=ESPN&queryType=MATCHUPS")
        assert response.status_code == 200


class TestOnboardThreadsOwner:
    def test_onboard_passes_owner_to_invoke(
        self, client, mock_table, mock_lambda_client
    ):
        mock_table.get_item.return_value = {}
        mock_lambda_client.invoke.return_value = {}
        response = client.post(
            "/leagues",
            json={"leagueId": "123", "platform": "SLEEPER", "season": "2024"},
        )
        assert response.status_code == 201
        import json

        payload = json.loads(mock_lambda_client.invoke.call_args.kwargs["Payload"])
        assert payload["ownerUserId"] == "user_1"


class TestTransferTokenEndpoint:
    def test_owner_mints_token(
        self, client, mock_table, league_lookup_item, league_metadata_item
    ):
        mock_table.get_item.side_effect = [
            {"Item": league_lookup_item},
            {"Item": league_metadata_item},
        ]
        mock_table.update_item.return_value = {}
        response = client.post("/leagues/123/transfer-token?platform=SLEEPER")
        assert response.status_code == 200
        assert response.json()["data"]["token"]
        kwargs = mock_table.update_item.call_args.kwargs
        assert "transfer_token_hash" in kwargs["UpdateExpression"]

    def test_non_owner_returns_403(
        self, client, mock_table, league_lookup_item, league_metadata_item
    ):
        mock_table.get_item.side_effect = [
            {"Item": league_lookup_item},
            {"Item": league_metadata_item},
        ]
        _as_user("intruder")
        response = client.post("/leagues/123/transfer-token?platform=SLEEPER")
        assert response.status_code == 403

    def test_update_failure_returns_500(
        self, client, mock_table, league_lookup_item, league_metadata_item
    ):
        mock_table.get_item.side_effect = [
            {"Item": league_lookup_item},
            {"Item": league_metadata_item},
        ]
        mock_table.update_item.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "InternalError", "Message": "x"}}, "UpdateItem"
        )
        response = client.post("/leagues/123/transfer-token?platform=SLEEPER")
        assert response.status_code == 500


class TestClaimOwnershipEndpoint:
    def _meta_with_token(self, token, expires_at):
        import hashlib

        return {
            "PK": "LEAGUE#canonical-abc",
            "SK": "METADATA",
            "owner_user_id": "user_1",
            "transfer_token_hash": hashlib.sha256(token.encode()).hexdigest(),
            "transfer_token_expires_at": expires_at,
        }

    def _future(self):
        from datetime import datetime, timedelta, timezone

        return (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

    def _past(self):
        from datetime import datetime, timedelta, timezone

        return (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()

    def test_happy_path_claims_ownership(self, client, mock_table, league_lookup_item):
        mock_table.get_item.side_effect = [
            {"Item": league_lookup_item},
            {"Item": self._meta_with_token("tok", self._future())},
        ]
        mock_table.update_item.return_value = {}
        _as_user("user_2")
        response = client.post(
            "/leagues/123/claim-ownership?platform=SLEEPER", json={"token": "tok"}
        )
        assert response.status_code == 200
        kwargs = mock_table.update_item.call_args.kwargs
        assert kwargs["ExpressionAttributeValues"][":caller"] == "user_2"
        assert "owner_user_id" in kwargs["UpdateExpression"]

    def test_no_token_returns_404(self, client, mock_table, league_lookup_item):
        mock_table.get_item.side_effect = [
            {"Item": league_lookup_item},
            {"Item": {"PK": "LEAGUE#canonical-abc", "SK": "METADATA"}},
        ]
        response = client.post(
            "/leagues/123/claim-ownership?platform=SLEEPER", json={"token": "tok"}
        )
        assert response.status_code == 404

    def test_mismatched_token_returns_403(self, client, mock_table, league_lookup_item):
        mock_table.get_item.side_effect = [
            {"Item": league_lookup_item},
            {"Item": self._meta_with_token("real", self._future())},
        ]
        response = client.post(
            "/leagues/123/claim-ownership?platform=SLEEPER", json={"token": "wrong"}
        )
        assert response.status_code == 403

    def test_expired_token_returns_410(self, client, mock_table, league_lookup_item):
        mock_table.get_item.side_effect = [
            {"Item": league_lookup_item},
            {"Item": self._meta_with_token("tok", self._past())},
        ]
        response = client.post(
            "/leagues/123/claim-ownership?platform=SLEEPER", json={"token": "tok"}
        )
        assert response.status_code == 410

    def test_unparseable_expiry_returns_410(
        self, client, mock_table, league_lookup_item
    ):
        mock_table.get_item.side_effect = [
            {"Item": league_lookup_item},
            {"Item": self._meta_with_token("tok", "not-a-date")},
        ]
        response = client.post(
            "/leagues/123/claim-ownership?platform=SLEEPER", json={"token": "tok"}
        )
        assert response.status_code == 410

    def test_race_conditional_failure_returns_409(
        self, client, mock_table, league_lookup_item
    ):
        mock_table.get_item.side_effect = [
            {"Item": league_lookup_item},
            {"Item": self._meta_with_token("tok", self._future())},
        ]
        mock_table.update_item.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "ConditionalCheckFailedException", "Message": "x"}},
            "UpdateItem",
        )
        response = client.post(
            "/leagues/123/claim-ownership?platform=SLEEPER", json={"token": "tok"}
        )
        assert response.status_code == 409

    def test_update_error_returns_500(self, client, mock_table, league_lookup_item):
        mock_table.get_item.side_effect = [
            {"Item": league_lookup_item},
            {"Item": self._meta_with_token("tok", self._future())},
        ]
        mock_table.update_item.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "InternalError", "Message": "x"}}, "UpdateItem"
        )
        response = client.post(
            "/leagues/123/claim-ownership?platform=SLEEPER", json={"token": "tok"}
        )
        assert response.status_code == 500


class TestVerifyMembershipEndpoint:
    _PAYLOAD: ClassVar = {"swid": "{abc}", "s2": "s2-token"}

    def _seasons_query(self, mock_table):
        mock_table.query.return_value = {
            "Items": [{"seasons": {"2023", "2024"}, "canonical_league_id": "x"}]
        }

    def test_non_espn_returns_400(self, client, mock_table, league_lookup_item):
        mock_table.get_item.return_value = {"Item": league_lookup_item}
        response = client.post(
            "/leagues/123/verify-membership?platform=SLEEPER", json=self._PAYLOAD
        )
        assert response.status_code == 400

    def test_valid_cookies_add_member(self, client, mock_table, league_lookup_item):
        mock_table.get_item.return_value = {"Item": league_lookup_item}
        self._seasons_query(mock_table)
        mock_table.update_item.return_value = {}
        espn_resp = MagicMock()
        espn_resp.raise_for_status = MagicMock()
        _as_user("user_2")
        with patch("main.http_requests.get", return_value=espn_resp):
            response = client.post(
                "/leagues/123/verify-membership?platform=ESPN", json=self._PAYLOAD
            )
        assert response.status_code == 200
        kwargs = mock_table.update_item.call_args.kwargs
        assert "ADD members" in kwargs["UpdateExpression"]
        assert kwargs["ExpressionAttributeValues"][":m"] == {"user_2"}

    def test_rejected_cookies_return_403(self, client, mock_table, league_lookup_item):
        import requests

        mock_table.get_item.return_value = {"Item": league_lookup_item}
        self._seasons_query(mock_table)
        espn_resp = MagicMock()
        err = requests.exceptions.HTTPError("401")
        err.response = MagicMock(status_code=401)
        espn_resp.raise_for_status.side_effect = err
        with patch("main.http_requests.get", return_value=espn_resp):
            response = client.post(
                "/leagues/123/verify-membership?platform=ESPN", json=self._PAYLOAD
            )
        assert response.status_code == 403
        mock_table.update_item.assert_not_called()

    def test_other_http_error_returns_502(self, client, mock_table, league_lookup_item):
        import requests

        mock_table.get_item.return_value = {"Item": league_lookup_item}
        self._seasons_query(mock_table)
        espn_resp = MagicMock()
        err = requests.exceptions.HTTPError("500")
        err.response = MagicMock(status_code=500)
        espn_resp.raise_for_status.side_effect = err
        with patch("main.http_requests.get", return_value=espn_resp):
            response = client.post(
                "/leagues/123/verify-membership?platform=ESPN", json=self._PAYLOAD
            )
        assert response.status_code == 502

    def test_request_error_returns_502(self, client, mock_table, league_lookup_item):
        import requests

        mock_table.get_item.return_value = {"Item": league_lookup_item}
        self._seasons_query(mock_table)
        with patch(
            "main.http_requests.get",
            side_effect=requests.exceptions.ConnectionError("boom"),
        ):
            response = client.post(
                "/leagues/123/verify-membership?platform=ESPN", json=self._PAYLOAD
            )
        assert response.status_code == 502
