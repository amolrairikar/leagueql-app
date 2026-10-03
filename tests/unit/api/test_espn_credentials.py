from unittest.mock import patch

import pytest


@pytest.fixture
def mock_engine():
    """Patch the shared engine class the API wrapper builds per call."""
    with patch("espn_credentials.EspnCredentialClient") as mock_cls:
        yield mock_cls


class TestApiEspnCredentials:
    def test_store_credentials_delegates_to_engine(self, mock_engine):
        import espn_credentials
        import main

        espn_credentials.store_credentials("user_1", "{abc}", "s2-token")

        mock_engine.assert_called_once_with(
            table=main.table,
            kms_client=main.kms_client,
            kms_key_id=main.ESPN_KMS_KEY_ID,
        )
        mock_engine.return_value.store_credentials.assert_called_once_with(
            "user_1", "{abc}", "s2-token"
        )

    def test_delete_credentials_delegates_to_engine(self, mock_engine):
        import espn_credentials

        espn_credentials.delete_credentials("user_1")

        mock_engine.return_value.delete_credentials.assert_called_once_with("user_1")
