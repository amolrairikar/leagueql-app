"""Tests for the shared src/common/secrets.py module."""

from unittest.mock import MagicMock, patch

from common import secrets


def test_get_ssm_parameter_returns_decrypted_value():
    mock_client = MagicMock()
    mock_client.get_parameter.return_value = {"Parameter": {"Value": "bs-token"}}
    with patch.object(secrets, "_ssm_client", mock_client):
        value = secrets.get_ssm_parameter("/leagueql/prod/betterstack/source_token")

    assert value == "bs-token"
    mock_client.get_parameter.assert_called_once_with(
        Name="/leagueql/prod/betterstack/source_token", WithDecryption=True
    )


def test_get_secret_from_env_param_fetches_when_set(monkeypatch):
    monkeypatch.setenv(
        "OTEL_EXPORTER_TOKEN_SSM_PARAM", "/leagueql/prod/betterstack/source_token"
    )
    mock_client = MagicMock()
    mock_client.get_parameter.return_value = {"Parameter": {"Value": "bs-token"}}
    with patch.object(secrets, "_ssm_client", mock_client):
        value = secrets.get_secret_from_env_param("OTEL_EXPORTER_TOKEN_SSM_PARAM")

    assert value == "bs-token"
    mock_client.get_parameter.assert_called_once_with(
        Name="/leagueql/prod/betterstack/source_token", WithDecryption=True
    )


def test_get_secret_from_env_param_returns_empty_when_unset(monkeypatch):
    monkeypatch.delenv("OTEL_EXPORTER_TOKEN_SSM_PARAM", raising=False)
    mock_client = MagicMock()
    # Unset env var -> no SSM call, empty string (module still imports unconfigured).
    with patch.object(secrets, "_ssm_client", mock_client):
        value = secrets.get_secret_from_env_param("OTEL_EXPORTER_TOKEN_SSM_PARAM")

    assert value == ""
    mock_client.get_parameter.assert_not_called()


def test_get_secret_from_env_param_returns_empty_when_blank(monkeypatch):
    monkeypatch.setenv("OTEL_EXPORTER_TOKEN_SSM_PARAM", "")
    mock_client = MagicMock()
    with patch.object(secrets, "_ssm_client", mock_client):
        value = secrets.get_secret_from_env_param("OTEL_EXPORTER_TOKEN_SSM_PARAM")

    assert value == ""
    mock_client.get_parameter.assert_not_called()
