"""Feature-flag evaluation backed by OpenFeature.

Vendored into every function's deployment zip. Flag state is read from the
``feature_flags.json`` config file sitting next to this module (bundled into each
Lambda by ``scripts/deployment_scripts/build_lambda_zip.sh``). The file maps a
flag name to ``{"enabled": <bool>}``; toggling a flag is a one-line edit to that
JSON followed by a redeploy. See
``docs/requirements/backend/BE-017-feature-flags.md``.

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
resolved — a missing config file, malformed JSON, an unknown flag — fails safe to
``False`` (feature off).
"""

import json
import logging
from pathlib import Path

from openfeature import api
from openfeature.provider.in_memory_provider import InMemoryFlag, InMemoryProvider

logger = logging.getLogger(__name__)

_CONFIG_PATH = Path(__file__).with_name("feature_flags.json")

# Per-feature paywall flag names (freemium model; see BE-014 / BE-017).
# Placeholder premium feature; not wired to any production endpoint yet.
PAYWALL_TEST_FEATURE = "paywall_test_feature"

# The variant names are cosmetic; what matters is the boolean each maps to.
_ON = "on"
_OFF = "off"


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


def _load_config() -> dict:
    """Read the flag config file, failing safe to an empty config."""
    try:
        with open(_CONFIG_PATH) as f:
            return json.load(f)
    except (OSError, ValueError) as exc:
        logger.warning(
            "Could not load feature flags from %s (%s); all flags default off",
            _CONFIG_PATH,
            exc,
        )
        return {}


def _set_provider_from_config(config: dict) -> None:
    api.set_provider(InMemoryProvider(_build_flags(config)))


_set_provider_from_config(_load_config())
_client = api.get_client()


def is_enabled(flag_name: str) -> bool:
    """Return whether ``flag_name`` is on, defaulting to ``False`` when unknown."""
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

    Lets a test exercise the ON path without editing the bundled config file:
    ``_override_for_testing({"billing": True})``.
    """
    _set_provider_from_config({name: {"enabled": on} for name, on in flags.items()})
