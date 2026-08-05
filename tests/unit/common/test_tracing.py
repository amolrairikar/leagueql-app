"""Tests for src/common/tracing.py — shared OTel bootstrap + W3C propagation (BE-020).

The disabled path is the default in tests and must be a true no-op (no provider, no
network, no instrumentation). The enabled wiring patches the lazily-imported OTel
pieces so no real global provider/instrumentation is installed. The inject↔extract
round-trip uses the real OpenTelemetry SDK with an in-memory exporter (the deps are
in the Pipfile) — it never touches the global tracer provider, so it stays isolated.
"""

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest

from common import tracing


@pytest.fixture(autouse=True)
def _reset_state():
    """``build_provider``/``init_tracing`` flip module globals; reset around each test."""
    tracing._provider = None
    tracing._initialized = False
    yield
    tracing._provider = None
    tracing._initialized = False


def _real_provider():
    """A real SDK provider + in-memory exporter (not registered globally)."""
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )

    provider = TracerProvider()
    exporter = InMemorySpanExporter()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return provider, exporter


class TestIsEnabled:
    def test_disabled_without_endpoint(self):
        with patch.object(tracing, "_OTLP_ENDPOINT", ""):
            assert tracing.is_enabled() is False

    def test_disabled_without_token(self):
        with (
            patch.object(tracing, "_OTLP_ENDPOINT", "https://in.example.com/v1/traces"),
            patch.object(tracing, "get_secret_from_env_param", return_value=""),
        ):
            assert tracing.is_enabled() is False

    def test_enabled_with_endpoint_and_token(self):
        with (
            patch.object(tracing, "_OTLP_ENDPOINT", "https://in.example.com/v1/traces"),
            patch.object(tracing, "get_secret_from_env_param", return_value="tok"),
        ):
            assert tracing.is_enabled() is True


class TestDisabledNoOp:
    def test_init_tracing_noop_when_unconfigured(self):
        with patch.object(tracing, "is_enabled", return_value=False):
            assert tracing.init_tracing("leagueql-onboarder") is False
            assert tracing._initialized is False
            assert tracing._provider is None

    def test_init_tracing_noop_when_already_initialized(self):
        tracing._initialized = True
        with patch.object(tracing, "is_enabled", return_value=True) as is_enabled:
            assert tracing.init_tracing("leagueql-onboarder") is False
            is_enabled.assert_not_called()

    def test_init_tracing_swallows_build_failure(self):
        with (
            patch.object(tracing, "is_enabled", return_value=True),
            patch.object(
                tracing, "build_provider", side_effect=RuntimeError("ssm down")
            ),
            patch.object(tracing, "logger") as mock_logger,
        ):
            assert tracing.init_tracing("leagueql-onboarder") is False
            assert tracing._initialized is False
            mock_logger.warning.assert_called_once()

    def test_inject_context_returns_empty_carrier(self):
        assert tracing.inject_context() == {}

    def test_inject_context_leaves_supplied_carrier_unchanged(self):
        carrier = {"correlation_id": "abc"}
        assert tracing.inject_context(carrier) == {"correlation_id": "abc"}
        assert "traceparent" not in carrier

    def test_extract_context_returns_none(self):
        assert tracing.extract_context({"traceparent": "00-x-y-01"}) is None

    def test_force_flush_is_safe(self):
        # Must not raise when no provider is installed.
        tracing.force_flush()

    def test_traced_handler_is_passthrough(self):
        with tracing.traced_handler("onboarder.handle", carrier={"x": "y"}) as span:
            assert span is None


@contextmanager
def _patched_otel():
    """Patch the OTel pieces ``build_provider`` imports lazily; yield the mocks."""
    with (
        patch.object(tracing, "get_secret_from_env_param", return_value="tok"),
        patch.object(tracing, "_OTLP_ENDPOINT", "https://in.example.com/v1/traces"),
        patch(
            "opentelemetry.exporter.otlp.proto.http.trace_exporter.OTLPSpanExporter"
        ) as exporter,
        patch("opentelemetry.sdk.trace.TracerProvider") as provider_cls,
        patch("opentelemetry.sdk.trace.export.BatchSpanProcessor"),
        patch("opentelemetry.sdk.resources.Resource"),
        patch("opentelemetry.trace.set_tracer_provider") as set_provider,
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
            "set_provider": set_provider,
            "boto_instr": boto_instr,
            "req_instr": req_instr,
        }


class TestBuildProvider:
    def test_builds_exporter_and_instruments(self):
        with _patched_otel() as mocks:
            provider = tracing.build_provider("leagueql-onboarder")
            # Exporter built with the OTLP endpoint + bearer-token auth header.
            _, kwargs = mocks["exporter"].call_args
            assert kwargs["endpoint"] == tracing._OTLP_ENDPOINT
            assert kwargs["headers"]["Authorization"] == "Bearer tok"
            assert "X-Axiom-Dataset" not in kwargs["headers"]
            # Provider registered globally; boto + requests instrumented; stored.
            mocks["set_provider"].assert_called_once()
            mocks["boto_instr"].return_value.instrument.assert_called_once()
            mocks["req_instr"].return_value.instrument.assert_called_once()
            assert provider is mocks["provider_cls"].return_value
            assert tracing._provider is provider

    def test_init_tracing_enabled_installs_and_marks_initialized(self):
        with (
            patch.object(tracing, "is_enabled", return_value=True),
            patch.object(tracing, "build_provider") as build_provider,
        ):
            assert tracing.init_tracing("leagueql-processor") is True
            assert tracing._initialized is True
            build_provider.assert_called_once_with("leagueql-processor")


class TestForceFlush:
    def test_flushes_installed_provider(self):
        provider = MagicMock()
        tracing._provider = provider
        tracing.force_flush()
        provider.force_flush.assert_called_once()

    def test_swallows_flush_error(self):
        provider = MagicMock()
        provider.force_flush.side_effect = RuntimeError("exporter down")
        tracing._provider = provider
        with patch.object(tracing, "logger") as mock_logger:
            tracing.force_flush()  # must not raise
            mock_logger.warning.assert_called_once()


class TestPropagationRoundTrip:
    def test_inject_then_extract_preserves_trace_id(self, monkeypatch):
        from opentelemetry import trace

        provider, _ = _real_provider()
        monkeypatch.setattr(tracing, "_provider", provider)
        tracer = provider.get_tracer("test")

        carrier: dict = {}
        with trace.use_span(tracer.start_span("parent"), end_on_exit=True) as parent:
            parent_trace_id = parent.get_span_context().trace_id
            tracing.inject_context(carrier)

        assert "traceparent" in carrier
        parent_ctx = tracing.extract_context(carrier)
        child = tracer.start_span("child", context=parent_ctx)
        assert child.get_span_context().trace_id == parent_trace_id
        child.end()

    def test_extract_from_lowercased_s3_style_metadata(self, monkeypatch):
        # S3 returns user-metadata keys lowercased; ``traceparent`` is already
        # lowercase, so the propagator round-trips a manifest's metadata carrier.
        provider, _ = _real_provider()
        monkeypatch.setattr(tracing, "_provider", provider)
        carrier = {
            "traceparent": "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01"
        }
        ctx = tracing.extract_context(carrier)
        child = provider.get_tracer("test").start_span("processor.handle", context=ctx)
        assert (
            format(child.get_span_context().trace_id, "032x")
            == "0af7651916cd43dd8448eb211c80319c"
        )
        child.end()

    def test_extract_context_none_for_empty_carrier_when_enabled(self):
        tracing._provider = MagicMock()
        assert tracing.extract_context({}) is None

    def test_inject_context_swallows_propagator_error(self):
        tracing._provider = MagicMock()
        with (
            patch(
                "opentelemetry.trace.propagation.tracecontext.TraceContextTextMapPropagator",
                side_effect=RuntimeError("boom"),
            ),
            patch.object(tracing, "logger") as mock_logger,
        ):
            carrier = {"correlation_id": "x"}
            assert tracing.inject_context(carrier) is carrier
            mock_logger.warning.assert_called_once()

    def test_extract_context_swallows_propagator_error(self):
        tracing._provider = MagicMock()
        with (
            patch(
                "opentelemetry.trace.propagation.tracecontext.TraceContextTextMapPropagator",
                side_effect=RuntimeError("boom"),
            ),
            patch.object(tracing, "logger") as mock_logger,
        ):
            assert tracing.extract_context({"traceparent": "x"}) is None
            mock_logger.warning.assert_called_once()


class TestTracedHandlerEnabled:
    def _fake_tracer(self, span):
        cm = MagicMock()
        cm.__enter__ = MagicMock(return_value=span)
        cm.__exit__ = MagicMock(return_value=False)
        tracer = MagicMock()
        tracer.start_as_current_span.return_value = cm
        return tracer

    def test_root_span_started_and_flushed(self):
        tracing._provider = MagicMock()
        fake_span = MagicMock()
        tracer = self._fake_tracer(fake_span)
        with (
            patch("opentelemetry.trace.get_tracer", return_value=tracer),
            patch.object(tracing, "force_flush") as flush,
        ):
            with tracing.traced_handler("sleeper_refresh.league", root=True) as span:
                assert span is fake_span
            # Root → no parent context extracted.
            _, kwargs = tracer.start_as_current_span.call_args
            assert kwargs["context"] is None
            flush.assert_called_once()

    def test_continuation_uses_extracted_parent_and_flushes(self):
        tracing._provider = MagicMock()
        sentinel_ctx = object()
        tracer = self._fake_tracer(MagicMock())
        with (
            patch.object(tracing, "extract_context", return_value=sentinel_ctx),
            patch("opentelemetry.trace.get_tracer", return_value=tracer),
            patch.object(tracing, "force_flush") as flush,
        ):
            with tracing.traced_handler(
                "processor.handle", carrier={"traceparent": "00-x-y-01"}
            ):
                pass
            _, kwargs = tracer.start_as_current_span.call_args
            assert kwargs["context"] is sentinel_ctx
            flush.assert_called_once()

    def test_flushes_even_when_body_raises(self):
        tracing._provider = MagicMock()
        tracer = self._fake_tracer(MagicMock())
        with (
            patch("opentelemetry.trace.get_tracer", return_value=tracer),
            patch.object(tracing, "force_flush") as flush,
        ):
            with pytest.raises(ValueError):
                with tracing.traced_handler("onboarder.handle", root=True):
                    raise ValueError("boom")
            flush.assert_called_once()
