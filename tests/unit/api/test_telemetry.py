"""Tests for src/api/telemetry.py — OTel tracing init for the API Lambda (BE-020).

The enabled path patches the lazily-imported OpenTelemetry pieces so no real
provider/exporter/instrumentation is installed (which would be a global side effect).
The disabled path is the default in tests and must be a true no-op.
"""

from contextlib import contextmanager
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _reset_init_flag():
    """``init_tracing`` flips a module-global; reset it around every test."""
    import telemetry

    telemetry._initialized = False
    yield
    telemetry._initialized = False


class TestIsEnabled:
    def test_disabled_without_dataset(self):
        import telemetry

        with patch.object(telemetry, "_AXIOM_DATASET", ""):
            assert telemetry.is_enabled() is False

    def test_disabled_without_token(self):
        import telemetry

        with (
            patch.object(telemetry, "_AXIOM_DATASET", "leagueql-dev"),
            patch.object(telemetry, "get_secret_from_env_param", return_value=""),
        ):
            assert telemetry.is_enabled() is False

    def test_enabled_with_token_and_dataset(self):
        import telemetry

        with (
            patch.object(telemetry, "_AXIOM_DATASET", "leagueql-dev"),
            patch.object(telemetry, "get_secret_from_env_param", return_value="tok"),
        ):
            assert telemetry.is_enabled() is True


class TestInitTracingDisabled:
    def test_noop_when_unconfigured(self):
        import telemetry

        with (
            patch.object(telemetry, "_AXIOM_DATASET", ""),
            patch.object(telemetry, "get_secret_from_env_param", return_value=""),
        ):
            app = FastAPI()
            assert telemetry.init_tracing(app) is False
            assert telemetry._initialized is False

    def test_noop_when_token_missing_even_with_dataset(self):
        import telemetry

        with (
            patch.object(telemetry, "_AXIOM_DATASET", "leagueql-dev"),
            patch.object(telemetry, "get_secret_from_env_param", return_value=""),
        ):
            assert telemetry.init_tracing(FastAPI()) is False
            assert telemetry._initialized is False

    def test_noop_when_already_initialized(self):
        import telemetry

        telemetry._initialized = True
        with patch.object(telemetry, "get_secret_from_env_param", return_value="tok"):
            assert telemetry.init_tracing(FastAPI()) is False

    def test_init_failure_is_swallowed(self):
        # A failing SSM read (param missing / IAM not propagated) must not crash the
        # API's import — tracing is disabled and the app keeps working.
        import telemetry

        with (
            patch.object(telemetry, "_AXIOM_DATASET", "leagueql-dev"),
            patch.object(
                telemetry,
                "get_secret_from_env_param",
                side_effect=RuntimeError("ssm down"),
            ),
            patch.object(telemetry, "logger") as mock_logger,
        ):
            assert telemetry.init_tracing(FastAPI()) is False
            assert telemetry._initialized is False
            mock_logger.warning.assert_called_once()


@contextmanager
def _patched_otel():
    """Patch the OTel pieces ``init_tracing`` imports lazily; yield the mocks."""
    import telemetry

    with (
        patch.object(telemetry, "_AXIOM_DATASET", "leagueql-dev"),
        patch.object(telemetry, "get_secret_from_env_param", return_value="tok"),
        patch(
            "opentelemetry.exporter.otlp.proto.http.trace_exporter.OTLPSpanExporter"
        ) as exporter,
        patch("opentelemetry.sdk.trace.TracerProvider") as provider_cls,
        patch("opentelemetry.sdk.trace.export.BatchSpanProcessor") as bsp,
        patch("opentelemetry.sdk.resources.Resource"),
        patch("opentelemetry.trace.set_tracer_provider") as set_provider,
        patch(
            "opentelemetry.instrumentation.fastapi.FastAPIInstrumentor"
        ) as fastapi_instr,
        patch(
            "opentelemetry.instrumentation.botocore.BotocoreInstrumentor"
        ) as boto_instr,
        patch(
            "opentelemetry.instrumentation.requests.RequestsInstrumentor"
        ) as req_instr,
    ):
        yield {
            "exporter": exporter,
            "provider_cls": provider_cls,
            "bsp": bsp,
            "set_provider": set_provider,
            "fastapi_instr": fastapi_instr,
            "boto_instr": boto_instr,
            "req_instr": req_instr,
        }


class TestInitTracingEnabled:
    def test_installs_provider_and_instrumentation(self):
        import telemetry

        app = FastAPI()
        with _patched_otel() as mocks:
            assert telemetry.init_tracing(app) is True
            assert telemetry._initialized is True
            # Exporter built with the Axiom endpoint + auth/dataset headers.
            _, kwargs = mocks["exporter"].call_args
            assert kwargs["headers"]["Authorization"] == "Bearer tok"
            assert kwargs["headers"]["X-Axiom-Dataset"] == "leagueql-dev"
            # Provider registered globally; app + boto + requests instrumented.
            mocks["set_provider"].assert_called_once()
            mocks["fastapi_instr"].instrument_app.assert_called_once_with(app)
            mocks["boto_instr"].return_value.instrument.assert_called_once()
            mocks["req_instr"].return_value.instrument.assert_called_once()

    def test_middleware_flushes_spans_per_request(self):
        import telemetry

        app = FastAPI()

        @app.get("/ping")
        def _ping():
            return {"ok": True}

        with _patched_otel() as mocks:
            telemetry.init_tracing(app)
            provider = mocks["provider_cls"].return_value
            resp = TestClient(app).get("/ping")
            assert resp.status_code == 200
            provider.force_flush.assert_called_once()

    def test_flush_failure_does_not_break_response(self):
        import telemetry

        app = FastAPI()

        @app.get("/ping")
        def _ping():
            return {"ok": True}

        with _patched_otel() as mocks:
            mocks["provider_cls"].return_value.force_flush.side_effect = RuntimeError(
                "axiom down"
            )
            with patch.object(telemetry, "logger") as mock_logger:
                telemetry.init_tracing(app)
                resp = TestClient(app).get("/ping")
                assert resp.status_code == 200
                mock_logger.warning.assert_called_once()
