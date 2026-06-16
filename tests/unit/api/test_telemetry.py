"""Tests for src/api/telemetry.py — FastAPI-specific OTel wiring (BE-020).

The shared provider/exporter/gating now lives in ``common.tracing`` (covered by
tests/unit/common/test_tracing.py). Here we only verify that ``telemetry.py`` gates
on ``is_enabled``, builds the shared provider as ``leagueql-api``, instruments the
FastAPI app, and flushes spans per request. The disabled path is the default in
tests and must be a true no-op.
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


class TestInitTracingDisabled:
    def test_noop_when_unconfigured(self):
        import telemetry

        with patch.object(telemetry, "is_enabled", return_value=False):
            app = FastAPI()
            assert telemetry.init_tracing(app) is False
            assert telemetry._initialized is False

    def test_noop_when_already_initialized(self):
        import telemetry

        telemetry._initialized = True
        with patch.object(telemetry, "is_enabled", return_value=True) as is_enabled:
            assert telemetry.init_tracing(FastAPI()) is False
            # The guard short-circuits before the gate is ever consulted.
            is_enabled.assert_not_called()

    def test_init_failure_is_swallowed(self):
        # A failing provider build (param missing / IAM not propagated / exporter
        # misconfig) must not crash the API's import — tracing is disabled and the
        # app keeps working.
        import telemetry

        with (
            patch.object(telemetry, "is_enabled", return_value=True),
            patch.object(
                telemetry.tracing,
                "build_provider",
                side_effect=RuntimeError("ssm down"),
            ),
            patch.object(telemetry, "logger") as mock_logger,
        ):
            assert telemetry.init_tracing(FastAPI()) is False
            assert telemetry._initialized is False
            mock_logger.warning.assert_called_once()


@contextmanager
def _patched_install():
    """Patch the shared builder + force_flush + FastAPIInstrumentor; yield the mocks.

    Lets the enabled path run without installing a real provider/exporter (a global
    side effect) — that wiring is verified directly against ``common.tracing``.
    """
    import telemetry

    with (
        patch.object(telemetry, "is_enabled", return_value=True),
        patch.object(telemetry.tracing, "build_provider") as build_provider,
        patch.object(telemetry.tracing, "force_flush") as force_flush,
        patch(
            "opentelemetry.instrumentation.fastapi.FastAPIInstrumentor"
        ) as fastapi_instr,
    ):
        yield {
            "build_provider": build_provider,
            "force_flush": force_flush,
            "fastapi_instr": fastapi_instr,
        }


class TestInitTracingEnabled:
    def test_builds_shared_provider_and_instruments_app(self):
        import telemetry

        app = FastAPI()
        with _patched_install() as mocks:
            assert telemetry.init_tracing(app) is True
            assert telemetry._initialized is True
            # Provider built via the shared module as the API service; app instrumented.
            mocks["build_provider"].assert_called_once_with("leagueql-api")
            mocks["fastapi_instr"].instrument_app.assert_called_once_with(app)

    def test_middleware_flushes_spans_per_request(self):
        import telemetry

        app = FastAPI()

        @app.get("/ping")
        def _ping():
            return {"ok": True}

        with _patched_install() as mocks:
            telemetry.init_tracing(app)
            resp = TestClient(app).get("/ping")
            assert resp.status_code == 200
            mocks["force_flush"].assert_called_once()
