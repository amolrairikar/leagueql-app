"""OpenTelemetry distributed tracing for the API Lambda → Better Stack (backend/otel-tracing).

The provider/exporter, endpoint/token gating, and ``botocore``/``requests``
instrumentation live in the shared :mod:`common.tracing` (also used by the async
onboarding chain, backend/otel-tracing). This module adds the **FastAPI-specific** pieces on top:
auto-instrumenting the app and force-flushing spans per request. The trace started
here is continued through the async chain via W3C context propagation (see backend/otel-tracing).

Design notes:
- No ``opentelemetry`` import happens at module load. The SDK / instrumentation are
  imported **lazily inside** :func:`_install_tracing` (and :mod:`common.tracing`),
  and only after the endpoint + token gate passes. So importing this module never
  requires the OTel packages, and the disabled path (unit tests, the Behave
  component suite, any unconfigured env) is a true no-op that makes zero network
  calls and instruments nothing.
- The OTLP ingest (source) token is sensitive: it is fetched at runtime from SSM by
  parameter *name* via :func:`common.secrets.get_secret_from_env_param` — never an
  env var / TF state / CI value.
- Spans are force-flushed per request because the Lambda execution environment freezes
  between invocations; otherwise buffered spans would be stranded and lost.
"""

from common import tracing
from common.logging_utils import logger
from common.tracing import is_enabled

# Guard against double-initialization (Mangum/FastAPI can re-import in some paths).
_initialized = False


def init_tracing(app) -> bool:
    """Install OTel tracing on the FastAPI ``app`` and export spans to Better Stack.

    A no-op (returns ``False``) when tracing is not configured or already initialized.
    Returns ``True`` when instrumentation was installed.

    Args:
        app: The FastAPI application to instrument.

    Returns:
        Whether tracing was installed on this call.
    """
    global _initialized
    if _initialized:
        return False

    try:
        if not is_enabled():
            logger.info("OTel tracing disabled: no OTLP endpoint/token configured")
            return False
        _install_tracing(app)
    except Exception:
        # Tracing setup must NEVER crash the API. This guards against, e.g., the SSM
        # parameter not existing yet (a deploy-ordering window), IAM not yet allowing
        # the read, or an exporter/instrumentation misconfiguration. On any failure
        # we disable tracing and keep serving requests untraced.
        logger.warning(
            "OTel tracing init failed; continuing without tracing", exc_info=True
        )
        return False

    _initialized = True
    logger.info("OTel tracing enabled → %s", tracing._OTLP_ENDPOINT)
    return True


def _install_tracing(app) -> None:
    """Build the shared provider, then add the FastAPI-specific instrumentation.

    The provider/exporter and botocore/requests instrumentation come from
    :func:`common.tracing.build_provider`; here we auto-instrument the FastAPI app
    (so an incoming ``traceparent`` from the browser, frontend/observability, continues that trace)
    and add a middleware that force-flushes spans before each response returns.
    """
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

    tracing.build_provider("leagueql-api")

    FastAPIInstrumentor.instrument_app(app)

    @app.middleware("http")
    async def _flush_spans(request, call_next):
        """Flush buffered spans before the response returns (Lambda freezes after)."""
        response = await call_next(request)
        tracing.force_flush()
        return response
