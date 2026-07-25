"""Tests for the shared src/common/secrets.py module."""

from unittest.mock import MagicMock, patch

import common.secrets as secrets


def test_get_ssm_parameter_returns_decrypted_value():
    mock_client = MagicMock()
    mock_client.get_parameter.return_value = {"Parameter": {"Value": "xaat-token"}}
    with patch.object(secrets, "_ssm_client", mock_client):
        value = secrets.get_ssm_parameter("/leagueql/prod/axiom/api_token")

    assert value == "xaat-token"
    mock_client.get_parameter.assert_called_once_with(
        Name="/leagueql/prod/axiom/api_token", WithDecryption=True
    )


def test_get_secret_from_env_param_fetches_when_set(monkeypatch):
    monkeypatch.setenv("AXIOM_API_TOKEN_SSM_PARAM", "/leagueql/prod/axiom/api_token")
    mock_client = MagicMock()
    mock_client.get_parameter.return_value = {"Parameter": {"Value": "xaat-token"}}
    with patch.object(secrets, "_ssm_client", mock_client):
        value = secrets.get_secret_from_env_param("AXIOM_API_TOKEN_SSM_PARAM")

    assert value == "xaat-token"
    mock_client.get_parameter.assert_called_once_with(
        Name="/leagueql/prod/axiom/api_token", WithDecryption=True
    )


def test_get_secret_from_env_param_returns_empty_when_unset(monkeypatch):
    monkeypatch.delenv("AXIOM_API_TOKEN_SSM_PARAM", raising=False)
    mock_client = MagicMock()
    # Unset env var -> no SSM call, empty string (module still imports unconfigured).
    with patch.object(secrets, "_ssm_client", mock_client):
        value = secrets.get_secret_from_env_param("AXIOM_API_TOKEN_SSM_PARAM")

    assert value == ""
    mock_client.get_parameter.assert_not_called()


def test_get_secret_from_env_param_returns_empty_when_blank(monkeypatch):
    monkeypatch.setenv("AXIOM_API_TOKEN_SSM_PARAM", "")
    mock_client = MagicMock()
    with patch.object(secrets, "_ssm_client", mock_client):
        value = secrets.get_secret_from_env_param("AXIOM_API_TOKEN_SSM_PARAM")

    assert value == ""
    mock_client.get_parameter.assert_not_called()
