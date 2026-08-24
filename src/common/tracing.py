"""Shared OpenTelemetry tracing bootstrap + W3C context propagation (backend/otel-tracing).

Vendored into every function's deployment zip via
``scripts/deployment_scripts/build_lambda_zip.sh``. Framework-agnostic: the API
Lambda layers FastAPI instrumentation on top in ``src/api/telemetry.py``; the async
onboarding chain (onboarder, processor, sleeper_refresh) uses :func:`init_tracing`
+ :func:`traced_handler` directly to continue the trace started upstream.

Design notes (mirroring ``src/api/telemetry.py``):
- No ``opentelemetry`` import happens at module load. The SDK / instrumentation are
  imported **lazily** and only after the endpoint + token gate passes, so importing
  this module never requires the OTel packages and the disabled path (unit tests,
  the Behave suite, any unconfigured env) is a true no-op that makes zero network
  calls and instruments nothing.
- The OTLP ingest (source) token is fetched at runtime from SSM by parameter *name*
  via :func:`common.secrets.get_secret_from_env_param`.
- Spans are force-flushed per invocation because the Lambda execution environment
  freezes between invocations; otherwise buffered spans would be stranded and lost.
- Tracing must **never** break a request/handler: every function here swallows its
  own errors and degrades to untraced.
"""

import os
from contextlib import contextmanager

from common.logging_utils import logger
from common.secrets import get_secret_from_env_param

# Non-sensitive config (plain env vars, set per-env by Terraform). The endpoint is
# the Better Stack source's OTLP traces URL (``https://<ingesting-host>/v1/traces``);
# there is no default because the ingesting host is account/source-specific.
_OTLP_ENDPOINT = os.environ.get("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", "")
_DEPLOYMENT_ENV = os.environ.get("ENVIRONMENT", "unknown")

# The installed provider, or None when tracing is disabled. Set by build_provider;
# used as the cheap (no SSM round-trip) gate for inject/extract/flush and to
# force_flush before a frozen Lambda invocation ends.
_provider = None

# Guard against double-initialization in the non-FastAPI Lambdas.
_initialized = False


def is_enabled() -> bool:
    """Return True when OTLP tracing is configured for this environment.

    Requires both an exporter endpoint (``OTEL_EXPORTER_OTLP_TRACES_ENDPOINT``) and
    an SSM parameter name for the source token (``OTEL_EXPORTER_TOKEN_SSM_PARAM``)
    that resolves to a non-empty value. Unconfigured contexts (tests, local) return
    False and tracing stays off.
    """
    if not _OTLP_ENDPOINT:
        return False
    return bool(get_secret_from_env_param("OTEL_EXPORTER_TOKEN_SSM_PARAM"))


def build_provider(service_name: str):
    """Build + register a ``TracerProvider`` exporting via OTLP and instrument
    ``botocore`` / ``requests`` (OTel imported lazily).

    Shared by the API (``src/api/telemetry.py``) and the async-chain Lambdas so the
    exporter config has a single source of truth. The caller is responsible for the
    ``is_enabled()`` gate and idempotency. Returns the provider (also stored in the
    module so :func:`force_flush` / :func:`traced_handler` can reach it).
    """
    global _provider
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.botocore import BotocoreInstrumentor
    from opentelemetry.instrumentation.requests import RequestsInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    token = get_secret_from_env_param("OTEL_EXPORTER_TOKEN_SSM_PARAM")
    resource = Resource.create(
        {
            "service.name": service_name,
            "deployment.environment": _DEPLOYMENT_ENV,
        }
    )
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(
        endpoint=_OTLP_ENDPOINT,
        headers={
            "Authorization": f"Bearer {token}",
        },
    )
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    # botocore/requests give child spans for DynamoDB/S3/Lambda + outbound HTTP.
    BotocoreInstrumentor().instrument()
    RequestsInstrumentor().instrument()

    _provider = provider
    return provider


def init_tracing(service_name: str) -> bool:
    """Install tracing for a (non-FastAPI) Lambda. Idempotent, gated, fail-safe.

    A no-op (returns ``False``) when tracing is not configured or already
    initialized. Returns ``True`` when instrumentation was installed on this call.

    Args:
        service_name: OTel ``service.name`` for this Lambda (e.g.
            ``leagueql-onboarder``).
    """
    global _initialized
    if _initialized:
        return False

    try:
        if not is_enabled():
            logger.info("OTel tracing disabled: no OTLP endpoint/token configured")
            return False
        build_provider(service_name)
    except Exception:
        # Tracing setup must NEVER crash the handler. Guards against the SSM
        # parameter not existing yet (a deploy-ordering window), IAM not yet
        # allowing the read, or an exporter/instrumentation misconfiguration.
        logger.warning(
            "OTel tracing init failed; continuing without tracing", exc_info=True
        )
        return False

    _initialized = True
    logger.info("OTel tracing enabled for %s → %s", service_name, _OTLP_ENDPOINT)
    return True


def inject_context(carrier: dict | None = None) -> dict:
    """Inject the current W3C trace context into ``carrier`` and return it.

    A no-op (returns ``carrier or {}`` unchanged) when tracing is disabled or no
    span is active, so callers can unconditionally attach the result to an invoke
    payload or S3 object metadata.
    """
    carrier = {} if carrier is None else carrier
    if _provider is None:
        return carrier
    try:
        from opentelemetry.trace.propagation.tracecontext import (
            TraceContextTextMapPropagator,
        )

        TraceContextTextMapPropagator().inject(carrier)
    except Exception:  # propagation must never break the caller
        logger.warning("OTel inject_context failed; carrier left untraced")
    return carrier


def extract_context(carrier):
    """Return an OTel ``Context`` extracted from ``carrier``, or ``None``.

    ``None`` when tracing is disabled, the carrier is empty/missing, or extraction
    fails — the caller then starts a fresh root span (normal OTel behavior).
    """
    if _provider is None or not carrier:
        return None
    try:
        from opentelemetry.trace.propagation.tracecontext import (
            TraceContextTextMapPropagator,
        )

        return TraceContextTextMapPropagator().extract(carrier)
    except Exception:  # a bad carrier must never break the handler
        logger.warning("OTel extract_context failed; starting a fresh trace")
        return None


def force_flush() -> None:
    """Flush buffered spans before a frozen Lambda invocation ends; never raises."""
    if _provider is None:
        return
    try:
        _provider.force_flush()
    except Exception:  # a flush failure must never break the handler
        logger.warning("OTel span force_flush failed")


@contextmanager
def traced_handler(span_name: str, *, carrier=None, root: bool = False):
    """Wrap a Lambda invocation in a span, then force-flush on exit.

    When tracing is disabled this is a bare pass-through (no span, no flush). When
    enabled, starts ``span_name`` as a **continuation** of ``carrier``'s trace (same
    ``trace_id``) — or a fresh **root** span when ``root`` is True or no usable
    carrier is present — and force-flushes in ``finally`` (the Lambda freezes
    between invocations, so buffered spans must be flushed before returning).

    Args:
        span_name: Name for the invocation span.
        carrier: A mapping (invoke payload sub-dict or S3 metadata) holding the
            upstream W3C ``traceparent``/``tracestate``; ignored when ``root``.
        root: Start a fresh root trace (used by the Sleeper cron, which has no
            inbound context to continue).
    """
    if _provider is None:
        yield None
        return

    from opentelemetry import trace

    parent = None if root else extract_context(carrier)
    tracer = trace.get_tracer(__name__)
    try:
        with tracer.start_as_current_span(span_name, context=parent) as span:
            yield span
    finally:
        force_flush()
