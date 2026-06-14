"""Unit tests for common.feature_flags (BE-017 OpenFeature flag layer)."""

import importlib
import json
import os

import boto3
import pytest

import common.feature_flags as ff

# AppConfig env vars the module reads at import to decide whether to source flags
# from AWS AppConfig. Cleared between tests so the default path stays offline.
_APPCONFIG_ENV = (
    "APPCONFIG_APPLICATION",
    "APPCONFIG_ENVIRONMENT",
    "APPCONFIG_PROFILE",
    "APPCONFIG_TTL_SECONDS",
)


@pytest.fixture(autouse=True)
def restore_default_flags():
    """Each test mutates the global OpenFeature provider (and some reload the
    module with AppConfig env set); restore the clean, no-AppConfig default
    afterward so state never leaks into other tests."""
    yield
    for key in _APPCONFIG_ENV:
        os.environ.pop(key, None)
    importlib.reload(ff)


class _FakeStream:
    """Stand-in for the StreamingBody returned in ``Configuration``."""

    def __init__(self, raw: bytes):
        self._raw = raw

    def read(self) -> bytes:
        return self._raw


class _FakeAppConfigClient:
    """Minimal ``appconfigdata`` client serving a queue of configurations."""

    def __init__(self, configs, start_error=None):
        # configs: objects to serve in order (dict → JSON bytes, None → empty body).
        self._configs = list(configs)
        self._start_error = start_error
        self.fail_next = None
        self.start_calls = 0
        self.latest_tokens: list[str] = []
        self._counter = 0

    def start_configuration_session(self, **kwargs):
        self.start_calls += 1
        if self._start_error:
            raise self._start_error
        return {"InitialConfigurationToken": "tok-0"}

    def get_latest_configuration(self, ConfigurationToken):
        self.latest_tokens.append(ConfigurationToken)
        if self.fail_next is not None:
            err = self.fail_next
            self.fail_next = None
            raise err
        obj = self._configs.pop(0) if self._configs else None
        raw = b"" if obj is None else json.dumps(obj).encode()
        self._counter += 1
        return {
            "NextPollConfigurationToken": f"tok-{self._counter}",
            "Configuration": _FakeStream(raw),
        }


def _reload_with_appconfig(monkeypatch, client, ttl="45"):
    """Reload the module with AppConfig wired and ``boto3.client`` faked."""
    monkeypatch.setenv("APPCONFIG_APPLICATION", "leagueql-dev")
    monkeypatch.setenv("APPCONFIG_ENVIRONMENT", "dev")
    monkeypatch.setenv("APPCONFIG_PROFILE", "feature-flags")
    monkeypatch.setenv("APPCONFIG_TTL_SECONDS", ttl)
    monkeypatch.setattr(boto3, "client", lambda *a, **k: client)
    return importlib.reload(ff)


class TestBillingFlag:
    def test_defaults_off_when_unconfigured(self):
        # With no AppConfig env vars (local / tests) there is no flag source, so
        # every flag — billing included — reads off and the Data API is never used.
        assert ff._appconfig_enabled is False
        assert ff._appconfigdata_client is None
        assert ff.is_billing_enabled() is False

    def test_override_on(self):
        ff._override_for_testing({"billing": True})
        assert ff.is_billing_enabled() is True

    def test_override_off(self):
        ff._override_for_testing({"billing": False})
        assert ff.is_billing_enabled() is False


class TestIsFeaturePaywalled:
    def test_both_flags_on_is_paywalled(self):
        ff._override_for_testing({"billing": True, "paywall_test_feature": True})
        assert ff.is_feature_paywalled("paywall_test_feature") is True

    def test_billing_off_is_not_paywalled(self):
        # Master flag off ⇒ no feature is paywalled, even if its own flag is on.
        ff._override_for_testing({"billing": False, "paywall_test_feature": True})
        assert ff.is_feature_paywalled("paywall_test_feature") is False

    def test_feature_flag_off_is_not_paywalled(self):
        # Billing on but the feature's own flag off ⇒ the feature is free.
        ff._override_for_testing({"billing": True, "paywall_test_feature": False})
        assert ff.is_feature_paywalled("paywall_test_feature") is False

    def test_unknown_feature_flag_is_not_paywalled(self):
        ff._override_for_testing({"billing": True})
        assert ff.is_feature_paywalled("does-not-exist") is False


class TestIsEnabled:
    def test_unknown_flag_defaults_false(self):
        ff._override_for_testing({"billing": True})
        assert ff.is_enabled("does-not-exist") is False

    def test_arbitrary_flag(self):
        ff._override_for_testing({"some_feature": True})
        assert ff.is_enabled("some_feature") is True


class TestBuildFlags:
    def test_missing_enabled_key_is_off(self):
        flags = ff._build_flags({"x": {}})
        assert flags["x"].default_variant == ff._OFF

    def test_non_dict_spec_is_off(self):
        flags = ff._build_flags({"x": "nonsense"})
        assert flags["x"].default_variant == ff._OFF

    def test_enabled_true_is_on(self):
        flags = ff._build_flags({"x": {"enabled": True}})
        assert flags["x"].default_variant == ff._ON


class TestAppConfigSource:
    def test_initial_load_from_appconfig(self, monkeypatch):
        client = _FakeAppConfigClient([{"billing": {"enabled": True}}])
        mod = _reload_with_appconfig(monkeypatch, client)
        assert mod._appconfig_enabled is True
        assert mod.is_billing_enabled() is True
        assert client.start_calls == 1

    def test_empty_payload_defaults_off(self, monkeypatch):
        # An empty body means "no deployment / no change" → all flags off.
        client = _FakeAppConfigClient([None])
        mod = _reload_with_appconfig(monkeypatch, client)
        assert mod.is_billing_enabled() is False

    def test_initial_fetch_error_defaults_off(self, monkeypatch):
        client = _FakeAppConfigClient([], start_error=RuntimeError("boom"))
        mod = _reload_with_appconfig(monkeypatch, client)
        assert mod.is_billing_enabled() is False

    def test_refresh_picks_up_change(self, monkeypatch):
        client = _FakeAppConfigClient(
            [{"billing": {"enabled": False}}, {"billing": {"enabled": True}}]
        )
        mod = _reload_with_appconfig(monkeypatch, client, ttl="0")
        # Initial load saw billing off...
        assert mod._cached_config == {"billing": {"enabled": False}}
        # ...and TTL=0 means the next read refreshes and picks up the new value.
        assert mod.is_billing_enabled() is True
        # The session token advances between polls (init used tok-0, refresh tok-1).
        assert client.latest_tokens[:2] == ["tok-0", "tok-1"]

    def test_refresh_within_ttl_skips_fetch(self, monkeypatch):
        client = _FakeAppConfigClient([{"billing": {"enabled": True}}])
        mod = _reload_with_appconfig(monkeypatch, client, ttl="3600")
        before = len(client.latest_tokens)
        mod.is_billing_enabled()
        mod.is_billing_enabled()
        assert len(client.latest_tokens) == before

    def test_refresh_error_keeps_last_known_and_resets_token(self, monkeypatch):
        client = _FakeAppConfigClient([{"billing": {"enabled": True}}])
        mod = _reload_with_appconfig(monkeypatch, client, ttl="0")
        assert mod.is_billing_enabled() is True
        client.fail_next = RuntimeError("transient")
        # A failed refresh keeps the last-known flags and drops the session so the
        # next poll re-establishes it.
        assert mod.is_billing_enabled() is True
        assert mod._session_token is None

    def test_unchanged_config_does_not_reset_provider(self, monkeypatch):
        client = _FakeAppConfigClient(
            [{"billing": {"enabled": True}}, {"billing": {"enabled": True}}]
        )
        mod = _reload_with_appconfig(monkeypatch, client, ttl="0")
        calls: list[dict] = []
        original = mod._set_provider_from_config
        monkeypatch.setattr(
            mod,
            "_set_provider_from_config",
            lambda config: calls.append(config) or original(config),
        )
        # Refresh fetches an identical config → provider is not re-registered.
        assert mod.is_billing_enabled() is True
        assert calls == []
