"""Tests for the BE-015 billing endpoints and the Clerk auth dependency."""

from types import SimpleNamespace
from unittest.mock import patch

import botocore.exceptions
import pytest
from fastapi import HTTPException


def _conditional_error() -> botocore.exceptions.ClientError:
    return botocore.exceptions.ClientError(
        {"Error": {"Code": "ConditionalCheckFailedException", "Message": "x"}},
        "UpdateItem",
    )


@pytest.fixture
def override_user():
    """Override the Clerk auth dependency so endpoints see a fixed user."""
    import main
    import routes

    main.app.dependency_overrides[routes.get_authenticated_user] = lambda: "user_1"
    yield "user_1"
    main.app.dependency_overrides.pop(routes.get_authenticated_user, None)


class TestGetAuthenticatedUser:
    def test_returns_sub_from_jwt_claims(self):
        from routes import get_authenticated_user

        request = SimpleNamespace(
            scope={
                "aws.event": {
                    "requestContext": {
                        "authorizer": {"jwt": {"claims": {"sub": "user_42"}}}
                    }
                }
            }
        )
        assert get_authenticated_user(request) == "user_42"

    def test_raises_401_when_no_claims(self):
        from routes import get_authenticated_user

        request = SimpleNamespace(scope={})
        with pytest.raises(HTTPException) as exc:
            get_authenticated_user(request)
        assert exc.value.status_code == 401


class TestCheckoutSessionEndpoint:
    def test_creates_session_with_trial(
        self,
        client,
        mock_table,
        league_lookup_item,
        league_metadata_item,
        override_user,
    ):
        league_metadata_item.pop("trial_used", None)
        mock_table.get_item.side_effect = [
            {"Item": league_lookup_item},  # lookup_league
            {"Item": league_metadata_item},  # get_league_metadata
            {"Item": {"stripe_customer_id": "cus_1"}},  # existing customer
        ]
        with patch("main.stripe") as mock_stripe:
            mock_stripe.checkout.Session.create.return_value = {"url": "https://c"}
            resp = client.post("/leagues/123/checkout-session?platform=SLEEPER")
        assert resp.status_code == 200
        assert resp.json()["data"]["url"] == "https://c"
        _, kwargs = mock_stripe.checkout.Session.create.call_args
        assert kwargs["subscription_data"]["trial_period_days"] == 14
        assert (
            kwargs["subscription_data"]["metadata"]["canonical_league_id"]
            == "canonical-abc"
        )
        assert kwargs["mode"] == "subscription"
        assert kwargs["allow_promotion_codes"] is True
        assert kwargs["managed_payments"] == {"enabled": True}

    def test_omits_trial_when_already_used(
        self,
        client,
        mock_table,
        league_lookup_item,
        league_metadata_item,
        override_user,
    ):
        league_metadata_item["trial_used"] = True
        mock_table.get_item.side_effect = [
            {"Item": league_lookup_item},
            {"Item": league_metadata_item},
            {"Item": {"stripe_customer_id": "cus_1"}},
        ]
        with patch("main.stripe") as mock_stripe:
            mock_stripe.checkout.Session.create.return_value = {"url": "https://c"}
            resp = client.post("/leagues/123/checkout-session?platform=SLEEPER")
        assert resp.status_code == 200
        _, kwargs = mock_stripe.checkout.Session.create.call_args
        assert "trial_period_days" not in kwargs["subscription_data"]

    def test_returns_409_when_checkout_slot_taken(
        self,
        client,
        mock_table,
        league_lookup_item,
        league_metadata_item,
        override_user,
    ):
        mock_table.get_item.side_effect = [
            {"Item": league_lookup_item},
            {"Item": league_metadata_item},
            {"Item": {"stripe_customer_id": "cus_1"}},
        ]
        mock_table.update_item.side_effect = _conditional_error()  # claim loses
        with patch("main.stripe") as mock_stripe:
            resp = client.post("/leagues/123/checkout-session?platform=SLEEPER")
        assert resp.status_code == 409
        mock_stripe.checkout.Session.create.assert_not_called()

    def test_requires_authentication(
        self, client, mock_table, league_lookup_item, league_metadata_item
    ):
        # No override and no aws.event in scope -> 401 from the dependency.
        resp = client.post("/leagues/123/checkout-session?platform=SLEEPER")
        assert resp.status_code == 401


class TestBillingPortalEndpoint:
    def test_returns_portal_url(self, client, mock_table, override_user):
        mock_table.get_item.return_value = {"Item": {"stripe_customer_id": "cus_1"}}
        with patch("main.stripe") as mock_stripe:
            mock_stripe.billing_portal.Session.create.return_value = {
                "url": "https://p"
            }
            resp = client.post("/billing-portal-session")
        assert resp.status_code == 200
        assert resp.json()["data"]["url"] == "https://p"

    def test_returns_404_when_no_customer(self, client, mock_table, override_user):
        mock_table.get_item.return_value = {}
        resp = client.post("/billing-portal-session")
        assert resp.status_code == 404
