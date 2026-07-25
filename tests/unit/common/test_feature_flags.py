"""Unit tests for common.feature_flags (BE-017 OpenFeature flag layer)."""

import importlib
import json
import os

import boto3
import pytest

import common.feature_flags as ff

# Env vars the module reads at import to decide whether to source flags from AWS SSM
# Parameter Store. Cleared between tests so the default path stays offline.
_FLAGS_ENV = (
    "FEATURE_FLAGS_SSM_PARAM",
    "FEATURE_FLAGS_TTL_SECONDS",
)


@pytest.fixture(autouse=True)
def restore_default_flags():
    """Each test mutates the global OpenFeature provider (and some reload the
    module with SSM env set); restore the clean, no-SSM default afterward so state
    never leaks into other tests."""
    yield
    for key in _FLAGS_ENV:
        os.environ.pop(key, None)
    importlib.reload(ff)


class _FakeSsmClient:
    """Minimal ``ssm`` client serving a queue of feature-flag parameter values."""

    def __init__(self, values, get_error=None):
        # values: objects to serve in order (dict → JSON value, None → empty value).
        # Once the queue drains the last value sticks, mirroring a real parameter that
        # keeps returning its current value on every GetParameter.
        self._values = list(values)
        self._get_error = get_error
        self.fail_next = None
        self.calls = 0
        self._last = None

    def get_parameter(self, Name):
        self.calls += 1
        if self._get_error is not None:
            raise self._get_error
        if self.fail_next is not None:
            err = self.fail_next
            self.fail_next = None
            raise err
        if self._values:
            self._last = self._values.pop(0)
        value = "" if self._last is None else json.dumps(self._last)
        return {"Parameter": {"Value": value}}


def _reload_with_ssm(monkeypatch, client, ttl="45"):
    """Reload the module with SSM wired and ``boto3.client`` faked."""
    monkeypatch.setenv("FEATURE_FLAGS_SSM_PARAM", "/leagueql/dev/feature-flags")
    monkeypatch.setenv("FEATURE_FLAGS_TTL_SECONDS", ttl)
    monkeypatch.setattr(boto3, "client", lambda *a, **k: client)
    return importlib.reload(ff)


class TestIsEnabled:
    def test_defaults_off_when_unconfigured(self):
        # With no SSM env var (local / tests) there is no flag source, so every flag
        # reads off and the SSM client is never created.
        assert ff._flags_enabled is False
        assert ff._ssm_client is None
        assert ff.is_enabled("banner") is False

    def test_override_on(self):
        ff._override_for_testing({"banner": True})
        assert ff.is_enabled("banner") is True

    def test_override_off(self):
        ff._override_for_testing({"banner": False})
        assert ff.is_enabled("banner") is False

    def test_unknown_flag_defaults_false(self):
        ff._override_for_testing({"banner": True})
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


class TestSsmSource:
    def test_initial_load_from_ssm(self, monkeypatch):
        client = _FakeSsmClient([{"banner": {"enabled": True}}])
        mod = _reload_with_ssm(monkeypatch, client)
        assert mod._flags_enabled is True
        assert mod.is_enabled("banner") is True
        assert client.calls == 1

    def test_empty_value_defaults_off(self, monkeypatch):
        # An empty parameter value means "no flags" → all flags off.
        client = _FakeSsmClient([None])
        mod = _reload_with_ssm(monkeypatch, client)
        assert mod.is_enabled("banner") is False

    def test_initial_fetch_error_defaults_off(self, monkeypatch):
        # A missing parameter (ParameterNotFound) or any error on the initial fetch
        # fails safe to all-off.
        client = _FakeSsmClient([], get_error=RuntimeError("ParameterNotFound"))
        mod = _reload_with_ssm(monkeypatch, client)
        assert mod.is_enabled("banner") is False

    def test_refresh_picks_up_change(self, monkeypatch):
        client = _FakeSsmClient(
            [{"banner": {"enabled": False}}, {"banner": {"enabled": True}}]
        )
        mod = _reload_with_ssm(monkeypatch, client, ttl="0")
        # Initial load saw the flag off...
        assert mod._cached_config == {"banner": {"enabled": False}}
        # ...and TTL=0 means the next read refreshes and picks up the new value.
        assert mod.is_enabled("banner") is True

    def test_refresh_within_ttl_skips_fetch(self, monkeypatch):
        client = _FakeSsmClient([{"banner": {"enabled": True}}])
        mod = _reload_with_ssm(monkeypatch, client, ttl="3600")
        before = client.calls
        mod.is_enabled("banner")
        mod.is_enabled("banner")
        assert client.calls == before

    def test_refresh_error_keeps_last_known(self, monkeypatch):
        client = _FakeSsmClient([{"banner": {"enabled": True}}])
        mod = _reload_with_ssm(monkeypatch, client, ttl="0")
        assert mod.is_enabled("banner") is True
        client.fail_next = RuntimeError("transient")
        # A failed refresh keeps the last-known flags rather than flipping to a
        # surprise state.
        assert mod.is_enabled("banner") is True

    def test_unchanged_config_does_not_reset_provider(self, monkeypatch):
        client = _FakeSsmClient(
            [{"banner": {"enabled": True}}, {"banner": {"enabled": True}}]
        )
        mod = _reload_with_ssm(monkeypatch, client, ttl="0")
        calls: list[dict] = []
        original = mod._set_provider_from_config
        monkeypatch.setattr(
            mod,
            "_set_provider_from_config",
            lambda config: calls.append(config) or original(config),
        )
        # Refresh fetches an identical config → provider is not re-registered.
        assert mod.is_enabled("banner") is True
        assert calls == []
