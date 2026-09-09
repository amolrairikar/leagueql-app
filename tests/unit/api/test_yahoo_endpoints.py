"""Unit tests for the Yahoo OAuth API routes and the onboarding gate."""

from unittest.mock import patch

import pytest


class TestYahooAuthorizeEndpoint:
    def test_returns_consent_url(self, client, mock_table):
        with (
            patch("yahoo_oauth.create_oauth_state", return_value="state-1") as mk_state,
            patch(
                "yahoo_oauth.build_authorize_url",
                return_value="https://api.login.yahoo.com/oauth2/request_auth?x=1",
            ) as mk_url,
        ):
            response = client.get("/auth/yahoo/authorize?leagueId=45.l.678")

        assert response.status_code == 200
        body = response.json()
        assert (
            body["data"]["authorize_url"]
            == "https://api.login.yahoo.com/oauth2/request_auth?x=1"
        )
        mk_state.assert_called_once_with("user_1", "45.l.678")
        mk_url.assert_called_once_with("state-1")

    def test_requires_league_id(self, client):
        response = client.get("/auth/yahoo/authorize")
        assert response.status_code == 422

    def test_unauthenticated_returns_401(self, client):
        import main
        import routes

        main.app.dependency_overrides.pop(routes.get_authenticated_user, None)
        try:
            response = client.get("/auth/yahoo/authorize?leagueId=1")
        finally:
            main.app.dependency_overrides[routes.get_authenticated_user] = lambda: (
                "user_1"
            )
        assert response.status_code == 401


class TestYahooCallbackEndpoint:
    def test_successful_link_redirects_with_marker(self, client):
        with (
            patch(
                "yahoo_oauth.consume_oauth_state",
                return_value={"clerk_user_id": "user_1", "league_id": "45.l.678"},
            ),
            patch(
                "yahoo_oauth.exchange_code_for_tokens",
                return_value={"access_token": "at", "refresh_token": "rt"},
            ),
            patch("yahoo_oauth.store_tokens") as mk_store,
        ):
            response = client.get(
                "/auth/yahoo/callback?code=abc&state=s1", follow_redirects=False
            )

        assert response.status_code == 302
        location = response.headers["location"]
        assert "platform=YAHOO" in location
        assert "yahooLinked=1" in location
        assert "leagueId=45.l.678" in location
        mk_store.assert_called_once()

    def test_declined_error_redirects_not_linked(self, client):
        response = client.get(
            "/auth/yahoo/callback?error=access_denied&state=s1",
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert "yahooLinked=0" in response.headers["location"]

    @pytest.mark.parametrize("query", ["state=s1", "code=abc"])
    def test_missing_code_or_state_redirects_not_linked(self, client, query):
        response = client.get(f"/auth/yahoo/callback?{query}", follow_redirects=False)
        assert response.status_code == 302
        assert "yahooLinked=0" in response.headers["location"]

    def test_invalid_state_redirects_not_linked(self, client):
        with patch("yahoo_oauth.consume_oauth_state", return_value=None):
            response = client.get(
                "/auth/yahoo/callback?code=abc&state=bad", follow_redirects=False
            )
        assert response.status_code == 302
        assert "yahooLinked=0" in response.headers["location"]

    def test_exchange_failure_redirects_not_linked_no_store(self, client):
        with (
            patch(
                "yahoo_oauth.consume_oauth_state",
                return_value={"clerk_user_id": "user_1", "league_id": "x"},
            ),
            patch(
                "yahoo_oauth.exchange_code_for_tokens",
                side_effect=RuntimeError("yahoo 500"),
            ),
            patch("yahoo_oauth.store_tokens") as mk_store,
        ):
            response = client.get(
                "/auth/yahoo/callback?code=abc&state=s1", follow_redirects=False
            )
        assert response.status_code == 302
        assert "yahooLinked=0" in response.headers["location"]
        mk_store.assert_not_called()


class TestYahooOnboardGate:
    def test_unlinked_returns_403(self, client):
        with patch("yahoo_oauth.has_valid_link", return_value=False):
            response = client.post(
                "/leagues", json={"leagueId": "45.l.678", "platform": "YAHOO"}
            )
        assert response.status_code == 403
        assert "Link your Yahoo account first" in response.json()["detail"]

    def test_linked_returns_coming_soon(self, client):
        with patch("yahoo_oauth.has_valid_link", return_value=True):
            response = client.post(
                "/leagues", json={"leagueId": "45.l.678", "platform": "YAHOO"}
            )
        assert response.status_code == 200
        assert response.json()["data"]["code"] == "YAHOO_COMING_SOON"
