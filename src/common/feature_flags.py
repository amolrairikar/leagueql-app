"""Feature-flag evaluation backed by OpenFeature.

Vendored into every function's deployment zip. Flag state lives in a single **AWS
SSM Parameter Store** parameter (a standard-tier ``String`` holding the flag JSON,
one per environment) and is read at runtime through the boto3 ``ssm``
``GetParameter`` API — so toggling a flag is an edit to the parameter value in the
SSM console, with **no redeploy**. Standard-tier parameters are free for both
storage and ``GetParameter`` calls. See
``docs/requirements/backend/BE-017-feature-flags.md``.

SSM is selected only when ``FEATURE_FLAGS_SSM_PARAM`` is set (the deployed
Lambdas). Otherwise — local dev and tests — there is **no flag source** and every
flag defaults to ``False`` (feature off). There is no bundled JSON fallback.

A ``billing`` master flag gates all Stripe billing behavior (BE-014 / BE-015):
when it is OFF, ``require_active_subscription`` is a no-op, the checkout and
billing-portal endpoints return 404, and the Stripe webhook no-ops.

On top of it, the ``premium_feature`` flag implements the freemium model: a
premium feature is paywalled only when **both** ``billing`` and ``premium_feature``
are ON (see ``is_feature_paywalled``). Every premium feature shares this one flag,
so they are all gated identically. The frontend gates the schedule-swap simulator
(FE-031) on it; no backend endpoint enforces it yet.

Evaluation goes through OpenFeature's in-memory provider so the rest of the app
depends only on the vendor-neutral OpenFeature client. Anything that cannot be
resolved — SSM unreachable, an unknown flag — fails safe to ``False``
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

# Shared premium-feature flag (freemium model; see BE-014 / BE-017). Every premium
# feature is gated identically on this one flag. The frontend gates the schedule-swap
# simulator (FE-031) on it; no backend endpoint enforces it yet.
PREMIUM_FEATURE = "premium_feature"

# Global, non-billing flag gating the in-app informational banner (FE-030) — a
# generic toggle reused for whatever the current banner promotes (Discord today).
# Surfaced to the SPA via GET /feature-flags; the backend enforces nothing.
BANNER = "banner"

# The variant names are cosmetic; what matters is the boolean each maps to.
_ON = "on"
_OFF = "off"

# SSM wiring (BE-017). When the parameter name is present the flag JSON is sourced
# from AWS SSM Parameter Store; otherwise (local / tests) every flag defaults off.
_FEATURE_FLAGS_SSM_PARAM = os.environ.get("FEATURE_FLAGS_SSM_PARAM")
# How long a fetched configuration is reused before the next poll (seconds). A
# console edit is picked up within this window.
_FEATURE_FLAGS_TTL_SECONDS = int(os.environ.get("FEATURE_FLAGS_TTL_SECONDS", "45"))

_flags_enabled = bool(_FEATURE_FLAGS_SSM_PARAM)
# Module-level boto3 client, mirroring the codebase's ssm/dynamo pattern. Only
# created when SSM is wired, so tests never touch the network.
_ssm_client = boto3.client("ssm") if _flags_enabled else None

# Mutable TTL cache state.
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


def _fetch_flags() -> dict:
    """Pull the latest flag JSON from the SSM parameter.

    The feature-flag parameter holds the same ``{name: {"enabled": bool}}`` shape
    ``_build_flags`` already parses. A missing parameter raises ``ParameterNotFound``,
    handled by the caller as a fetch error (fail-safe to the last-known / all-off
    config).
    """
    response = _ssm_client.get_parameter(Name=_FEATURE_FLAGS_SSM_PARAM)
    raw = response["Parameter"]["Value"]
    if not raw:
        return {}
    return json.loads(raw)


def _refresh_if_stale() -> None:
    """Refresh the cached flags from SSM once the TTL has elapsed.

    A fetch failure (network, missing parameter, malformed JSON) keeps the
    last-known flags — flags never flip to a surprise state because SSM hiccuped.
    """
    global _cached_config, _last_refresh_at
    now = time.monotonic()
    if now - _last_refresh_at < _FEATURE_FLAGS_TTL_SECONDS:
        return
    _last_refresh_at = now
    try:
        config = _fetch_flags()
    except Exception as exc:
        logger.warning("Feature-flag refresh failed (%s); using last-known flags", exc)
        return
    if config != _cached_config:
        _cached_config = config
        _set_provider_from_config(config)


def _initialize() -> None:
    """Seed the provider at import: from SSM when wired, else all-off."""
    global _cached_config, _last_refresh_at
    if not _flags_enabled:
        _set_provider_from_config({})
        return
    try:
        _cached_config = _fetch_flags()
    except Exception as exc:
        logger.warning(
            "Initial feature-flag fetch failed (%s); all flags default off", exc
        )
        _cached_config = {}
    _last_refresh_at = time.monotonic()
    _set_provider_from_config(_cached_config)


_initialize()
_client = api.get_client()


def is_enabled(flag_name: str) -> bool:
    """Return whether ``flag_name`` is on, defaulting to ``False`` when unknown."""
    if _flags_enabled:
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

    Lets a test exercise the ON path without standing up SSM:
    ``_override_for_testing({"billing": True})``.
    """
    _set_provider_from_config({name: {"enabled": on} for name, on in flags.items()})
