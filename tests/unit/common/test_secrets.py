"""Tests for the shared src/common/secrets.py module."""

from unittest.mock import MagicMock, patch

import common.secrets as secrets


def test_get_ssm_parameter_returns_decrypted_value():
    mock_client = MagicMock()
    mock_client.get_parameter.return_value = {"Parameter": {"Value": "sk_live_xyz"}}
    with patch.object(secrets, "_ssm_client", mock_client):
        value = secrets.get_ssm_parameter("/leagueql/prod/stripe/secret_key")

    assert value == "sk_live_xyz"
    mock_client.get_parameter.assert_called_once_with(
        Name="/leagueql/prod/stripe/secret_key", WithDecryption=True
    )


def test_get_secret_from_env_param_fetches_when_set(monkeypatch):
    monkeypatch.setenv(
        "STRIPE_SECRET_KEY_SSM_PARAM", "/leagueql/prod/stripe/secret_key"
    )
    mock_client = MagicMock()
    mock_client.get_parameter.return_value = {"Parameter": {"Value": "whsec_abc"}}
    with patch.object(secrets, "_ssm_client", mock_client):
        value = secrets.get_secret_from_env_param("STRIPE_SECRET_KEY_SSM_PARAM")

    assert value == "whsec_abc"
    mock_client.get_parameter.assert_called_once_with(
        Name="/leagueql/prod/stripe/secret_key", WithDecryption=True
    )


def test_get_secret_from_env_param_returns_empty_when_unset(monkeypatch):
    monkeypatch.delenv("STRIPE_SECRET_KEY_SSM_PARAM", raising=False)
    mock_client = MagicMock()
    # Unset env var -> no SSM call, empty string (module still imports unconfigured).
    with patch.object(secrets, "_ssm_client", mock_client):
        value = secrets.get_secret_from_env_param("STRIPE_SECRET_KEY_SSM_PARAM")

    assert value == ""
    mock_client.get_parameter.assert_not_called()


def test_get_secret_from_env_param_returns_empty_when_blank(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY_SSM_PARAM", "")
    mock_client = MagicMock()
    with patch.object(secrets, "_ssm_client", mock_client):
        value = secrets.get_secret_from_env_param("STRIPE_SECRET_KEY_SSM_PARAM")

    assert value == ""
    mock_client.get_parameter.assert_not_called()
