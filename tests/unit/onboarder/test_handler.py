"""Tests for onboarder/handler.py."""

import json
from unittest.mock import ANY, MagicMock, patch

import requests


class TestTraceContextPropagation:
    """The handler continues the upstream trace carried in the event (BE-020)."""

    def test_handler_continues_trace_from_event_carrier(self, onboarder_handler):
        event = {"trace_context": {"traceparent": "00-abc-def-01"}}
        with (
            patch.object(
                onboarder_handler, "_handle", return_value={"statusCode": 200}
            ) as impl,
            patch.object(onboarder_handler, "traced_handler") as th,
        ):
            result = onboarder_handler.lambda_handler(event, MagicMock())

        assert result == {"statusCode": 200}
        th.assert_called_once_with(
            "onboarder.handle", carrier={"traceparent": "00-abc-def-01"}
        )
        impl.assert_called_once_with(event, ANY)

    def test_handler_passes_none_carrier_when_absent(self, onboarder_handler):
        with (
            patch.object(
                onboarder_handler, "_handle", return_value={"statusCode": 200}
            ),
            patch.object(onboarder_handler, "traced_handler") as th,
        ):
            onboarder_handler.lambda_handler({}, MagicMock())
        th.assert_called_once_with("onboarder.handle", carrier=None)


class TestLambdaHandlerMissingFields:
    def test_missing_body_returns_400(self, onboarder_handler):
        result = onboarder_handler.lambda_handler(
            {"requestType": "ONBOARD"}, MagicMock()
        )
        assert result["statusCode"] == 400
        assert "Missing required event field" in json.loads(result["body"])["error_msg"]

    def test_missing_request_type_returns_400(self, onboarder_handler):
        result = onboarder_handler.lambda_handler(
            {"body": {"leagueId": "123"}}, MagicMock()
        )
        assert result["statusCode"] == 400


class TestLambdaHandlerSleeperRefreshNoCanonicalId:
    def test_canonical_id_resolved_successfully(self, onboarder_handler):
        event = {
            "requestType": "REFRESH",
            "body": {"leagueId": "new-lg", "platform": "SLEEPER"},
        }
        mock_svc = MagicMock()
        mock_svc.canonical_league_id = "canonical-abc"

        with (
            patch.object(
                onboarder_handler,
                "resolve_sleeper_canonical_league_id",
                return_value="canonical-abc",
            ),
            patch.object(
                onboarder_handler,
                "OnboardingService",
                return_value=mock_svc,
            ),
        ):
            result = onboarder_handler.lambda_handler(event, MagicMock())

        assert result["statusCode"] == 200

    def test_canonical_id_not_found_returns_404(self, onboarder_handler):
        event = {
            "requestType": "REFRESH",
            "body": {"leagueId": "new-lg", "platform": "SLEEPER"},
        }
        with patch.object(
            onboarder_handler,
            "resolve_sleeper_canonical_league_id",
            return_value=None,
        ):
            result = onboarder_handler.lambda_handler(event, MagicMock())
        assert result["statusCode"] == 404

    def test_http_error_in_canonical_resolution_returns_502(self, onboarder_handler):
        event = {
            "requestType": "REFRESH",
            "body": {"leagueId": "new-lg", "platform": "SLEEPER"},
        }
        with patch.object(
            onboarder_handler,
            "resolve_sleeper_canonical_league_id",
            side_effect=requests.exceptions.HTTPError("err"),
        ):
            result = onboarder_handler.lambda_handler(event, MagicMock())
        assert result["statusCode"] == 502

    def test_generic_error_in_canonical_resolution_returns_500(self, onboarder_handler):
        event = {
            "requestType": "REFRESH",
            "body": {"leagueId": "new-lg", "platform": "SLEEPER"},
        }
        with patch.object(
            onboarder_handler,
            "resolve_sleeper_canonical_league_id",
            side_effect=RuntimeError("unexpected"),
        ):
            result = onboarder_handler.lambda_handler(event, MagicMock())
        assert result["statusCode"] == 500


class TestLambdaHandlerServiceInitErrors:
    def test_key_error_in_init_returns_400(self, onboarder_handler):
        event = {
            "requestType": "ONBOARD",
            "body": {"platform": "SLEEPER"},
        }
        with patch.object(
            onboarder_handler, "OnboardingService", side_effect=KeyError("leagueId")
        ):
            result = onboarder_handler.lambda_handler(event, MagicMock())
        assert result["statusCode"] == 400

    def test_value_error_in_init_returns_400(self, onboarder_handler):
        event = {
            "requestType": "ONBOARD",
            "body": {"leagueId": "123", "platform": "YAHOO"},
        }
        with patch.object(
            onboarder_handler,
            "OnboardingService",
            side_effect=ValueError("Unsupported platform"),
        ):
            result = onboarder_handler.lambda_handler(event, MagicMock())
        assert result["statusCode"] == 400

    def test_http_error_in_init_returns_502(self, onboarder_handler):
        event = {
            "requestType": "ONBOARD",
            "body": {"leagueId": "123", "platform": "ESPN", "season": "2024"},
        }
        with patch.object(
            onboarder_handler,
            "OnboardingService",
            side_effect=requests.exceptions.HTTPError("403"),
        ):
            result = onboarder_handler.lambda_handler(event, MagicMock())
        assert result["statusCode"] == 502

    def test_runtime_error_in_init_returns_502(self, onboarder_handler):
        event = {
            "requestType": "ONBOARD",
            "body": {"leagueId": "123", "platform": "SLEEPER"},
        }
        with patch.object(
            onboarder_handler,
            "OnboardingService",
            side_effect=RuntimeError("API failure"),
        ):
            result = onboarder_handler.lambda_handler(event, MagicMock())
        assert result["statusCode"] == 502


class TestLambdaHandlerRunErrors:
    def _make_service_mock(self, run_side_effect):
        svc = MagicMock()
        svc.canonical_league_id = "canonical-abc"
        svc.run.side_effect = run_side_effect
        return svc

    def test_key_error_during_run_returns_500(self, onboarder_handler):
        event = {
            "requestType": "ONBOARD",
            "body": {"leagueId": "123", "platform": "SLEEPER"},
        }
        svc = self._make_service_mock(KeyError("S3_BUCKET_NAME"))
        with patch.object(onboarder_handler, "OnboardingService", return_value=svc):
            result = onboarder_handler.lambda_handler(event, MagicMock())
        assert result["statusCode"] == 500

    def test_runtime_error_during_run_returns_502(self, onboarder_handler):
        event = {
            "requestType": "ONBOARD",
            "body": {"leagueId": "123", "platform": "SLEEPER"},
        }
        svc = self._make_service_mock(RuntimeError("S3 error"))
        with patch.object(onboarder_handler, "OnboardingService", return_value=svc):
            result = onboarder_handler.lambda_handler(event, MagicMock())
        assert result["statusCode"] == 502

    def test_http_error_during_run_returns_502(self, onboarder_handler):
        event = {
            "requestType": "ONBOARD",
            "body": {"leagueId": "123", "platform": "ESPN", "season": "2024"},
        }
        err = requests.exceptions.HTTPError("503")
        err.response = MagicMock(status_code=503)
        svc = self._make_service_mock(err)
        with patch.object(onboarder_handler, "OnboardingService", return_value=svc):
            result = onboarder_handler.lambda_handler(event, MagicMock())
        assert result["statusCode"] == 502

    def test_generic_exception_during_run_returns_500(self, onboarder_handler):
        event = {
            "requestType": "ONBOARD",
            "body": {"leagueId": "123", "platform": "SLEEPER"},
        }
        svc = self._make_service_mock(Exception("unexpected"))
        with patch.object(onboarder_handler, "OnboardingService", return_value=svc):
            result = onboarder_handler.lambda_handler(event, MagicMock())
        assert result["statusCode"] == 500

    def test_reprocess_all_forwarded_to_service(self, onboarder_handler):
        # BE-019: the backfill flag on the invoke payload reaches OnboardingService.
        event = {
            "requestType": "REFRESH",
            "canonicalLeagueId": "canonical-abc",
            "reprocessAll": True,
            "body": {"leagueId": "123", "platform": "SLEEPER"},
        }
        svc = MagicMock()
        svc.canonical_league_id = "canonical-abc"
        with patch.object(
            onboarder_handler, "OnboardingService", return_value=svc
        ) as mock_cls:
            onboarder_handler.lambda_handler(event, MagicMock())
        assert mock_cls.call_args.kwargs["reprocess_all"] is True


class TestLambdaHandlerNoStartedSeasons:
    """A league that resolves to no started seasons (only pre_draft/drafting) is a
    user error for ONBOARD and a no-op success for REFRESH/MIGRATE."""

    def _make_service_mock(self):
        svc = MagicMock()
        svc.canonical_league_id = "canonical-abc"
        svc.client.get_seasons.return_value = []
        return svc

    def test_onboard_no_started_seasons_returns_400_not_started(
        self, onboarder_handler
    ):
        event = {
            "requestType": "ONBOARD",
            "correlation_id": "corr-1",
            "body": {"leagueId": "123", "platform": "SLEEPER"},
        }
        svc = self._make_service_mock()
        with (
            patch.object(onboarder_handler, "OnboardingService", return_value=svc),
            patch.object(onboarder_handler, "write_job_status") as mock_wjs,
        ):
            result = onboarder_handler.lambda_handler(event, MagicMock())
        assert result["statusCode"] == 400
        svc.run.assert_not_called()
        args, kwargs = mock_wjs.call_args
        assert args[1] == "FAILED"
        assert kwargs["failure_code"] == "NOT_STARTED"

    def test_refresh_no_started_seasons_returns_200_completed(self, onboarder_handler):
        event = {
            "requestType": "REFRESH",
            "correlation_id": "corr-1",
            "canonicalLeagueId": "canonical-abc",
            "body": {"leagueId": "league-2026", "platform": "SLEEPER"},
        }
        svc = self._make_service_mock()
        with (
            patch.object(onboarder_handler, "OnboardingService", return_value=svc),
            patch.object(onboarder_handler, "write_job_status") as mock_wjs,
        ):
            result = onboarder_handler.lambda_handler(event, MagicMock())
        assert result["statusCode"] == 200
        assert json.loads(result["body"])["status"] == "succeeded"
        svc.run.assert_not_called()
        assert mock_wjs.call_args.args[1] == "COMPLETED"


class TestLambdaHandlerRecordsJobStatus:
    """Failure branches must record a FAILED JOB_STATUS with the right code."""

    def _assert_failed(self, mock_wjs, expected_code):
        mock_wjs.assert_called_once()
        args, kwargs = mock_wjs.call_args
        assert args[1] == "FAILED"
        assert kwargs["failure_code"] == expected_code

    def test_espn_http_error_records_espn_auth(self, onboarder_handler):
        event = {
            "requestType": "ONBOARD",
            "correlation_id": "corr-1",
            "body": {"leagueId": "123", "platform": "ESPN", "season": "2024"},
        }
        err = requests.exceptions.HTTPError("403")
        err.response = MagicMock(status_code=403)
        with (
            patch.object(onboarder_handler, "OnboardingService", side_effect=err),
            patch.object(onboarder_handler, "write_job_status") as mock_wjs,
        ):
            result = onboarder_handler.lambda_handler(event, MagicMock())
        assert result["statusCode"] == 502
        self._assert_failed(mock_wjs, "ESPN_AUTH")

    def test_value_error_records_invalid_input(self, onboarder_handler):
        event = {
            "requestType": "ONBOARD",
            "correlation_id": "corr-1",
            "body": {"leagueId": "123", "platform": "YAHOO"},
        }
        with (
            patch.object(
                onboarder_handler,
                "OnboardingService",
                side_effect=ValueError("Unsupported platform"),
            ),
            patch.object(onboarder_handler, "write_job_status") as mock_wjs,
        ):
            result = onboarder_handler.lambda_handler(event, MagicMock())
        assert result["statusCode"] == 400
        self._assert_failed(mock_wjs, "INVALID_INPUT")

    def test_sleeper_not_found_records_not_found(self, onboarder_handler):
        event = {
            "requestType": "REFRESH",
            "correlation_id": "corr-1",
            "body": {"leagueId": "new-lg", "platform": "SLEEPER"},
        }
        with (
            patch.object(
                onboarder_handler,
                "resolve_sleeper_canonical_league_id",
                return_value=None,
            ),
            patch.object(onboarder_handler, "write_job_status") as mock_wjs,
        ):
            result = onboarder_handler.lambda_handler(event, MagicMock())
        assert result["statusCode"] == 404
        self._assert_failed(mock_wjs, "NOT_FOUND")

    def test_runtime_error_during_run_records_upstream(self, onboarder_handler):
        event = {
            "requestType": "ONBOARD",
            "correlation_id": "corr-1",
            "body": {"leagueId": "123", "platform": "SLEEPER"},
        }
        svc = MagicMock()
        svc.canonical_league_id = "canonical-abc"
        svc.run.side_effect = RuntimeError("S3 error")
        with (
            patch.object(onboarder_handler, "OnboardingService", return_value=svc),
            patch.object(onboarder_handler, "write_job_status") as mock_wjs,
        ):
            result = onboarder_handler.lambda_handler(event, MagicMock())
        assert result["statusCode"] == 502
        self._assert_failed(mock_wjs, "UPSTREAM")


class TestLambdaHandlerSystemicAlerting:
    """publish_failure (SNS alert) fires only for systemic failure codes, not for
    expected user errors — recorded for the user but not paged on."""

    def test_espn_auth_user_error_does_not_publish(self, onboarder_handler):
        """An ESPN 403 -> ESPN_AUTH is the user's expired cookies; no alert."""
        event = {
            "requestType": "ONBOARD",
            "correlation_id": "corr-1",
            "body": {"leagueId": "123", "platform": "ESPN", "season": "2024"},
        }
        err = requests.exceptions.HTTPError("403")
        err.response = MagicMock(status_code=403)
        with (
            patch.object(onboarder_handler, "OnboardingService", side_effect=err),
            patch.object(onboarder_handler, "write_job_status"),
            patch.object(onboarder_handler, "publish_failure") as mock_pub,
        ):
            onboarder_handler.lambda_handler(event, MagicMock())
        mock_pub.assert_not_called()

    def test_not_found_user_error_does_not_publish(self, onboarder_handler):
        event = {
            "requestType": "REFRESH",
            "correlation_id": "corr-1",
            "body": {"leagueId": "new-lg", "platform": "SLEEPER"},
        }
        with (
            patch.object(
                onboarder_handler,
                "resolve_sleeper_canonical_league_id",
                return_value=None,
            ),
            patch.object(onboarder_handler, "write_job_status"),
            patch.object(onboarder_handler, "publish_failure") as mock_pub,
        ):
            onboarder_handler.lambda_handler(event, MagicMock())
        mock_pub.assert_not_called()

    def test_upstream_systemic_error_publishes(self, onboarder_handler):
        """A RuntimeError during run -> UPSTREAM is our/the platform's problem; alert."""
        event = {
            "requestType": "ONBOARD",
            "correlation_id": "corr-1",
            "body": {"leagueId": "123", "platform": "SLEEPER"},
        }
        svc = MagicMock()
        svc.canonical_league_id = "canonical-abc"
        svc.run.side_effect = RuntimeError("S3 error")
        with (
            patch.object(onboarder_handler, "OnboardingService", return_value=svc),
            patch.object(onboarder_handler, "write_job_status"),
            patch.object(onboarder_handler, "publish_failure") as mock_pub,
        ):
            onboarder_handler.lambda_handler(event, MagicMock())
        mock_pub.assert_called_once()
        assert "S3 error" in mock_pub.call_args.args[0]

    def test_record_failure_systemic_without_detail_uses_fallback(
        self, onboarder_handler
    ):
        """Defensive: a systemic code with no error_detail still publishes a
        meaningful message rather than None."""
        with (
            patch.object(onboarder_handler, "write_job_status"),
            patch.object(onboarder_handler, "publish_failure") as mock_pub,
        ):
            onboarder_handler._record_failure("ONBOARD", "INTERNAL")
        mock_pub.assert_called_once()
        assert "INTERNAL" in mock_pub.call_args.args[0]


class TestLambdaHandlerSuccess:
    def test_returns_200_with_canonical_id(self, onboarder_handler):
        event = {
            "requestType": "ONBOARD",
            "body": {"leagueId": "123", "platform": "SLEEPER"},
        }
        mock_svc = MagicMock()
        mock_svc.canonical_league_id = "canonical-abc"
        mock_svc.run = MagicMock()

        with patch.object(
            onboarder_handler, "OnboardingService", return_value=mock_svc
        ):
            result = onboarder_handler.lambda_handler(event, MagicMock())

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["status"] == "succeeded"
        assert body["canonical_league_id"] == "canonical-abc"

    def test_espn_onboard_with_season(self, onboarder_handler):
        event = {
            "requestType": "ONBOARD",
            "body": {
                "leagueId": "456",
                "platform": "ESPN",
                "season": "2024",
                "s2": "abc",
                "swid": "{xyz}",
            },
        }
        mock_svc = MagicMock()
        mock_svc.canonical_league_id = "espn-id"
        mock_svc.run = MagicMock()

        with patch.object(
            onboarder_handler, "OnboardingService", return_value=mock_svc
        ):
            result = onboarder_handler.lambda_handler(event, MagicMock())

        assert result["statusCode"] == 200

    def test_sleeper_refresh_with_existing_canonical_id(self, onboarder_handler):
        event = {
            "requestType": "REFRESH",
            "canonicalLeagueId": "existing-canonical",
            "body": {"leagueId": "123", "platform": "SLEEPER"},
        }
        mock_svc = MagicMock()
        mock_svc.canonical_league_id = "existing-canonical"
        mock_svc.run = MagicMock()

        with patch.object(
            onboarder_handler, "OnboardingService", return_value=mock_svc
        ):
            result = onboarder_handler.lambda_handler(event, MagicMock())

        assert result["statusCode"] == 200
