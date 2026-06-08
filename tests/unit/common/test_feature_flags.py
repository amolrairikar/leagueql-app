"""Unit tests for common.feature_flags (BE-017 OpenFeature flag layer)."""

from pathlib import Path

import pytest

import common.feature_flags as ff


@pytest.fixture(autouse=True)
def restore_default_flags():
    """Each test mutates the global OpenFeature provider; reload the shipped
    config afterward so state does not leak into other test modules."""
    yield
    ff._set_provider_from_config(ff._load_config())


class TestBillingFlag:
    def test_ships_off_by_default(self):
        # The bundled feature_flags.json sets billing to disabled.
        ff._set_provider_from_config(ff._load_config())
        assert ff.is_billing_enabled() is False

    def test_override_on(self):
        ff._override_for_testing({"billing": True})
        assert ff.is_billing_enabled() is True

    def test_override_off(self):
        ff._override_for_testing({"billing": False})
        assert ff.is_billing_enabled() is False


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


class TestLoadConfigFailSafe:
    def test_missing_file_returns_empty(self, monkeypatch):
        monkeypatch.setattr(ff, "_CONFIG_PATH", Path("/no/such/feature_flags.json"))
        assert ff._load_config() == {}

    def test_malformed_json_returns_empty(self, tmp_path, monkeypatch):
        bad = tmp_path / "feature_flags.json"
        bad.write_text("{ not valid json")
        monkeypatch.setattr(ff, "_CONFIG_PATH", bad)
        assert ff._load_config() == {}

    def test_missing_file_makes_billing_off(self, monkeypatch):
        monkeypatch.setattr(ff, "_CONFIG_PATH", Path("/no/such/feature_flags.json"))
        ff._set_provider_from_config(ff._load_config())
        assert ff.is_billing_enabled() is False
