"""OpenTelemetry distributed tracing for the API Lambda → Axiom (BE-020).

Scoped to **this** Lambda only. The async onboarding chain (Onboarder → Processor →
Sleeper Refresh) intentionally stays on the lightweight ``correlation_id`` mechanism;
do not add OTel there.

Design notes:
- No ``opentelemetry`` import happens at module load. The SDK / instrumentation are
  imported **lazily inside** :func:`init_tracing`, and only after the Axiom token +
  dataset gate passes. So importing this module never requires the OTel packages, and
  the disabled path (unit tests, the Behave component suite, any unconfigured env) is a
  true no-op that makes zero network calls and instruments nothing.
- The Axiom ingest token is sensitive: it is fetched at runtime from SSM by parameter
  *name* via :func:`common.secrets.get_secret_from_env_param` (same pattern as the
  Stripe secret key, BE-015) — never an env var / TF state / CI value.
- Spans are force-flushed per request because the Lambda execution environment freezes
  between invocations; otherwise buffered spans would be stranded and lost.
"""

import os

from common.logging_utils import logger
from common.secrets import get_secret_from_env_param

# Non-sensitive config (plain env vars, set per-env by Terraform).
_AXIOM_TRACES_URL = os.environ.get("AXIOM_TRACES_URL", "https://api.axiom.co/v1/traces")
_AXIOM_DATASET = os.environ.get("AXIOM_DATASET", "")
_DEPLOYMENT_ENV = os.environ.get("ENVIRONMENT", "unknown")

# Guard against double-initialization (Mangum/FastAPI can re-import in some paths).
_initialized = False


def is_enabled() -> bool:
    """Return True when Axiom tracing is configured for this environment.

    Requires both an SSM parameter name for the token (``AXIOM_API_TOKEN_SSM_PARAM``,
    resolving to a non-empty value) and a dataset (``AXIOM_DATASET``). Unconfigured
    contexts (tests, local) return False and tracing stays off.
    """
    if not _AXIOM_DATASET:
        return False
    return bool(get_secret_from_env_param("AXIOM_API_TOKEN_SSM_PARAM"))


def init_tracing(app) -> bool:
    """Install OTel tracing on the FastAPI ``app`` and export spans to Axiom.

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
        token = get_secret_from_env_param("AXIOM_API_TOKEN_SSM_PARAM")
        if not token or not _AXIOM_DATASET:
            logger.info("OTel tracing disabled: no Axiom token/dataset configured")
            return False
        _install_tracing(app, token)
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
    logger.info("OTel tracing enabled → Axiom dataset %s", _AXIOM_DATASET)
    return True


def _install_tracing(app, token: str) -> None:
    """Build the provider/exporter and instrument the app (OTel imported lazily)."""
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.botocore import BotocoreInstrumentor
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.requests import RequestsInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    resource = Resource.create(
        {
            "service.name": "leagueql-api",
            "deployment.environment": _DEPLOYMENT_ENV,
        }
    )
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(
        endpoint=_AXIOM_TRACES_URL,
        headers={
            "Authorization": f"Bearer {token}",
            "X-Axiom-Dataset": _AXIOM_DATASET,
        },
    )
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    # FastAPI auto-extracts an incoming ``traceparent`` and continues the browser's
    # trace (FE-029). botocore/requests give child spans for DynamoDB/Lambda + HTTP.
    FastAPIInstrumentor.instrument_app(app)
    BotocoreInstrumentor().instrument()
    RequestsInstrumentor().instrument()

    @app.middleware("http")
    async def _flush_spans(request, call_next):
        """Flush buffered spans before the response returns (Lambda freezes after)."""
        response = await call_next(request)
        try:
            provider.force_flush()
        except Exception:  # a flush failure must never break the response
            logger.warning("OTel span force_flush failed")
        return response
