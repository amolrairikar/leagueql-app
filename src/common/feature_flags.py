"""Feature-flag evaluation backed by OpenFeature.

Vendored into every function's deployment zip. Flag state lives in **AWS
AppConfig** (a feature-flag configuration profile, per environment) and is read
at runtime through the boto3 ``appconfigdata`` Data API — so toggling a flag is a
console change + AppConfig deployment, with **no redeploy**. See
``docs/requirements/backend/BE-017-feature-flags.md``.

AppConfig is selected only when ``APPCONFIG_APPLICATION`` / ``APPCONFIG_ENVIRONMENT``
/ ``APPCONFIG_PROFILE`` are all set (the deployed Lambdas). Otherwise — local dev
and tests — there is **no flag source** and every flag defaults to ``False``
(feature off). There is no bundled JSON fallback.

A ``billing`` master flag gates all Stripe billing behavior (BE-014 / BE-015):
when it is OFF, ``require_active_subscription`` is a no-op, the checkout and
billing-portal endpoints return 404, and the Stripe webhook no-ops.

On top of it, per-feature ``paywall_*`` flags implement the freemium model: a
premium feature is paywalled only when **both** ``billing`` and that feature's
flag are ON (see ``is_feature_paywalled``). No production endpoint is gated yet —
``paywall_test_feature`` is a placeholder kept so the mechanism, pricing table,
and config are wired and ready for the first real premium feature.

Evaluation goes through OpenFeature's in-memory provider so the rest of the app
depends only on the vendor-neutral OpenFeature client. Anything that cannot be
resolved — AppConfig unreachable, an unknown flag — fails safe to ``False``
(feature off).
"""

import json
import logging
import os
import time

import boto3
from openfeature import api
from openfeature.provider.in_memory_provider import InMemoryFlag, InMemoryProvider

logger = logging.getLogger(__name__)

# Per-feature paywall flag names (freemium model; see BE-014 / BE-017).
# Placeholder premium feature; not wired to any production endpoint yet.
PAYWALL_TEST_FEATURE = "paywall_test_feature"

# The variant names are cosmetic; what matters is the boolean each maps to.
_ON = "on"
_OFF = "off"

# AppConfig wiring (BE-017). When all three identifiers are present the flag JSON
# is sourced from AWS AppConfig; otherwise (local / tests) every flag defaults off.
_APPCONFIG_APPLICATION = os.environ.get("APPCONFIG_APPLICATION")
_APPCONFIG_ENVIRONMENT = os.environ.get("APPCONFIG_ENVIRONMENT")
_APPCONFIG_PROFILE = os.environ.get("APPCONFIG_PROFILE")
# How long a fetched configuration is reused before the next poll (seconds). A
# console toggle is picked up within this window after its AppConfig deployment.
_APPCONFIG_TTL_SECONDS = int(os.environ.get("APPCONFIG_TTL_SECONDS", "45"))

_appconfig_enabled = bool(
    _APPCONFIG_APPLICATION and _APPCONFIG_ENVIRONMENT and _APPCONFIG_PROFILE
)
# Module-level boto3 client, mirroring the codebase's ssm/dynamo pattern. Only
# created when AppConfig is wired, so tests never touch the network.
_appconfigdata_client = boto3.client("appconfigdata") if _appconfig_enabled else None

# Mutable Data API session + TTL cache state.
_session_token: str | None = None
_cached_config: dict = {}
_last_refresh_at: float = 0.0


def _build_flags(config: dict) -> dict[str, InMemoryFlag]:
    """Turn a ``{name: {"enabled": bool}}`` config into OpenFeature flags."""
    flags: dict[str, InMemoryFlag] = {}
    for name, spec in config.items():
        enabled = bool(spec.get("enabled", False)) if isinstance(spec, dict) else False
        flags[name] = InMemoryFlag(
            default_variant=_ON if enabled else _OFF,
            variants={_ON: True, _OFF: False},
        )
    return flags


def _set_provider_from_config(config: dict) -> None:
    api.set_provider(InMemoryProvider(_build_flags(config)))


def _fetch_appconfig() -> dict | None:
    """Pull the latest flag JSON from AppConfig, advancing the session token.

    Returns the parsed flag config, or ``None`` when AppConfig responds with an
    empty body (no change since the last poll) so the caller keeps the cached
    value. The feature-flag profile serves the same ``{name: {"enabled": bool}}``
    shape ``_build_flags`` already parses.
    """
    global _session_token
    if _session_token is None:
        session = _appconfigdata_client.start_configuration_session(
            ApplicationIdentifier=_APPCONFIG_APPLICATION,
            EnvironmentIdentifier=_APPCONFIG_ENVIRONMENT,
            ConfigurationProfileIdentifier=_APPCONFIG_PROFILE,
        )
        _session_token = session["InitialConfigurationToken"]

    response = _appconfigdata_client.get_latest_configuration(
        ConfigurationToken=_session_token
    )
    # Each response carries the token to use on the *next* poll; not advancing it
    # breaks the session.
    _session_token = response["NextPollConfigurationToken"]
    raw = response["Configuration"].read()
    if not raw:
        return None
    return json.loads(raw)


def _refresh_if_stale() -> None:
    """Refresh the cached flags from AppConfig once the TTL has elapsed.

    A fetch failure (network, expired token, malformed JSON) keeps the last-known
    flags and drops the session so the next poll re-establishes it — flags never
    flip to a surprise state because AppConfig hiccuped.
    """
    global _cached_config, _last_refresh_at, _session_token
    now = time.monotonic()
    if now - _last_refresh_at < _APPCONFIG_TTL_SECONDS:
        return
    _last_refresh_at = now
    try:
        config = _fetch_appconfig()
    except Exception as exc:
        logger.warning("AppConfig refresh failed (%s); using last-known flags", exc)
        _session_token = None
        return
    if config is not None and config != _cached_config:
        _cached_config = config
        _set_provider_from_config(config)


def _initialize() -> None:
    """Seed the provider at import: from AppConfig when wired, else all-off."""
    global _cached_config, _last_refresh_at
    if not _appconfig_enabled:
        _set_provider_from_config({})
        return
    try:
        _cached_config = _fetch_appconfig() or {}
    except Exception as exc:
        logger.warning(
            "Initial AppConfig fetch failed (%s); all flags default off", exc
        )
        _cached_config = {}
    _last_refresh_at = time.monotonic()
    _set_provider_from_config(_cached_config)


_initialize()
_client = api.get_client()


def is_enabled(flag_name: str) -> bool:
    """Return whether ``flag_name`` is on, defaulting to ``False`` when unknown."""
    if _appconfig_enabled:
        _refresh_if_stale()
    return _client.get_boolean_value(flag_name, False)


def is_billing_enabled() -> bool:
    """Return whether Stripe billing (BE-014 / BE-015) is enabled."""
    return is_enabled("billing")


def is_feature_paywalled(flag_name: str) -> bool:
    """Return whether a premium feature is paywalled (freemium model; BE-014).

    A feature is paywalled only when **both** the ``billing`` master flag and the
    feature's own ``flag_name`` are ON. With billing off (the default) this is
    always ``False``, so every feature is free.
    """
    return is_billing_enabled() and is_enabled(flag_name)


def _override_for_testing(flags: dict[str, bool]) -> None:
    """Replace the active provider with an explicit flag map (tests only).

    Lets a test exercise the ON path without standing up AppConfig:
    ``_override_for_testing({"billing": True})``.
    """
    _set_provider_from_config({name: {"enabled": on} for name, on in flags.items()})
