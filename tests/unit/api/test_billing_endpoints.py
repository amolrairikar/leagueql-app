"""Tests for the BE-015 billing endpoints and the Clerk auth dependency."""

from types import SimpleNamespace
from unittest.mock import patch

import botocore.exceptions
import pytest
import stripe
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


class TestEnsureStripeApiKey:
    """The Stripe secret key is resolved lazily (BE-015) — off the cold-start init
    path — and cached per execution environment."""

    def test_resolves_and_sets_api_key_from_ssm(self):
        import main

        main._resolve_stripe_api_key.cache_clear()
        try:
            with (
                patch(
                    "main.get_secret_from_env_param", return_value="sk_test_x"
                ) as mock_get,
                patch("main.stripe") as mock_stripe,
            ):
                main.ensure_stripe_api_key()
                assert mock_stripe.api_key == "sk_test_x"
                mock_get.assert_called_once_with("STRIPE_SECRET_KEY_SSM_PARAM")
        finally:
            main._resolve_stripe_api_key.cache_clear()

    def test_caches_resolution_so_ssm_is_fetched_once(self):
        import main

        main._resolve_stripe_api_key.cache_clear()
        try:
            with (
                patch(
                    "main.get_secret_from_env_param", return_value="sk_test_y"
                ) as mock_get,
                patch("main.stripe") as mock_stripe,
            ):
                main.ensure_stripe_api_key()
                main.ensure_stripe_api_key()
                assert mock_stripe.api_key == "sk_test_y"
                mock_get.assert_called_once()
        finally:
            main._resolve_stripe_api_key.cache_clear()


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
            {},  # trial_used_for_league (no durable marker)
            {"Item": {"stripe_customer_id": "cus_1"}},  # existing customer
        ]
        with patch("main.stripe") as mock_stripe:
            mock_stripe.checkout.Session.create.return_value = {"url": "https://c"}
            resp = client.post("/leagues/123/checkout-session?platform=SLEEPER")
        assert resp.status_code == 200
        assert resp.json()["data"]["url"] == "https://c"
        _, kwargs = mock_stripe.checkout.Session.create.call_args
        assert kwargs["subscription_data"]["trial_period_days"] == 14
        metadata = kwargs["subscription_data"]["metadata"]
        assert metadata["canonical_league_id"] == "canonical-abc"
        assert metadata["platform"] == "SLEEPER"
        assert metadata["native_league_id"] == "123"
        assert kwargs["mode"] == "subscription"
        assert kwargs["allow_promotion_codes"] is True
        assert kwargs["managed_payments"] == {"enabled": True}

    def test_omits_trial_when_durable_marker_present(
        self,
        client,
        mock_table,
        league_lookup_item,
        league_metadata_item,
        override_user,
    ):
        # No METADATA trial_used, but a durable (platform, league_id) record exists
        # from a prior trial before this league was deleted and re-onboarded.
        league_metadata_item.pop("trial_used", None)
        mock_table.get_item.side_effect = [
            {"Item": league_lookup_item},  # lookup_league
            {"Item": league_metadata_item},  # get_league_metadata
            {  # trial_used_for_league: durable marker present
                "Item": {
                    "PK": "LEAGUE#123#PLATFORM#SLEEPER",
                    "SK": "TRIAL_USED",
                }
            },
            {"Item": {"stripe_customer_id": "cus_1"}},  # existing customer
        ]
        with patch("main.stripe") as mock_stripe:
            mock_stripe.checkout.Session.create.return_value = {"url": "https://c"}
            resp = client.post("/leagues/123/checkout-session?platform=SLEEPER")
        assert resp.status_code == 200
        _, kwargs = mock_stripe.checkout.Session.create.call_args
        assert "trial_period_days" not in kwargs["subscription_data"]

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
        league_metadata_item.pop("trial_used", None)
        mock_table.get_item.side_effect = [
            {"Item": league_lookup_item},
            {"Item": league_metadata_item},
            {},  # trial_used_for_league (no durable marker)
            {"Item": {"stripe_customer_id": "cus_1"}},
        ]
        mock_table.update_item.side_effect = _conditional_error()  # claim loses
        with patch("main.stripe") as mock_stripe:
            resp = client.post("/leagues/123/checkout-session?platform=SLEEPER")
        assert resp.status_code == 409
        mock_stripe.checkout.Session.create.assert_not_called()

    def test_recovers_when_stored_customer_deleted(
        self,
        client,
        mock_table,
        league_lookup_item,
        league_metadata_item,
        override_user,
    ):
        # The stored Stripe customer was deleted out-of-band: the first session
        # create raises "No such customer"; checkout mints a fresh customer and
        # retries successfully (BE-015).
        league_metadata_item["trial_used"] = True
        mock_table.get_item.side_effect = [
            {"Item": league_lookup_item},
            {"Item": league_metadata_item},
            {"Item": {"stripe_customer_id": "cus_old"}},  # deleted in Stripe
        ]
        with patch("main.stripe") as mock_stripe:
            mock_stripe.checkout.Session.create.side_effect = [
                stripe.error.InvalidRequestError(
                    "No such customer: cus_old", "customer"
                ),
                {"url": "https://c"},
            ]
            mock_stripe.Customer.create.return_value = {"id": "cus_new"}
            resp = client.post("/leagues/123/checkout-session?platform=SLEEPER")
        assert resp.status_code == 200
        assert resp.json()["data"]["url"] == "https://c"
        # A new customer was minted and the retry targeted it.
        mock_stripe.Customer.create.assert_called_once()
        assert mock_stripe.checkout.Session.create.call_count == 2
        retry_kwargs = mock_stripe.checkout.Session.create.call_args_list[1].kwargs
        assert retry_kwargs["customer"] == "cus_new"
        # The stored mapping was overwritten with the new customer id.
        user_writes = [
            c.kwargs["Item"]
            for c in mock_table.put_item.call_args_list
            if c.kwargs.get("Item", {}).get("SK") == "USER"
        ]
        assert user_writes and user_writes[-1]["stripe_customer_id"] == "cus_new"

    def test_returns_502_on_non_customer_invalid_request(
        self,
        client,
        mock_table,
        league_lookup_item,
        league_metadata_item,
        override_user,
    ):
        # A non-customer Stripe validation error is surfaced as 502, no recovery.
        league_metadata_item["trial_used"] = True
        mock_table.get_item.side_effect = [
            {"Item": league_lookup_item},
            {"Item": league_metadata_item},
            {"Item": {"stripe_customer_id": "cus_1"}},
        ]
        with patch("main.stripe") as mock_stripe:
            mock_stripe.checkout.Session.create.side_effect = (
                stripe.error.InvalidRequestError("Bad price", "line_items")
            )
            resp = client.post("/leagues/123/checkout-session?platform=SLEEPER")
        assert resp.status_code == 502
        mock_stripe.Customer.create.assert_not_called()

    def test_returns_502_on_stripe_error(
        self,
        client,
        mock_table,
        league_lookup_item,
        league_metadata_item,
        override_user,
    ):
        # A transient Stripe failure surfaces as 502 (JSON detail + CORS headers)
        # rather than an uncaught 500 the browser can't read.
        league_metadata_item["trial_used"] = True
        mock_table.get_item.side_effect = [
            {"Item": league_lookup_item},
            {"Item": league_metadata_item},
            {"Item": {"stripe_customer_id": "cus_1"}},
        ]
        with patch("main.stripe") as mock_stripe:
            mock_stripe.checkout.Session.create.side_effect = (
                stripe.error.APIConnectionError("network down")
            )
            resp = client.post("/leagues/123/checkout-session?platform=SLEEPER")
        assert resp.status_code == 502
        mock_stripe.Customer.create.assert_not_called()

    def test_returns_502_when_recovery_retry_fails(
        self,
        client,
        mock_table,
        league_lookup_item,
        league_metadata_item,
        override_user,
    ):
        # Recovery recreates the customer but the retried session create also
        # fails -> 502.
        league_metadata_item["trial_used"] = True
        mock_table.get_item.side_effect = [
            {"Item": league_lookup_item},
            {"Item": league_metadata_item},
            {"Item": {"stripe_customer_id": "cus_old"}},
        ]
        with patch("main.stripe") as mock_stripe:
            mock_stripe.checkout.Session.create.side_effect = [
                stripe.error.InvalidRequestError("No such customer", "customer"),
                stripe.error.APIConnectionError("network down"),
            ]
            mock_stripe.Customer.create.return_value = {"id": "cus_new"}
            resp = client.post("/leagues/123/checkout-session?platform=SLEEPER")
        assert resp.status_code == 502
        mock_stripe.Customer.create.assert_called_once()

    def test_returns_500_when_recreated_mapping_write_fails(
        self,
        client,
        mock_table,
        league_lookup_item,
        league_metadata_item,
        override_user,
    ):
        # Recovery mints a new customer but persisting the mapping fails -> 500.
        league_metadata_item["trial_used"] = True
        mock_table.get_item.side_effect = [
            {"Item": league_lookup_item},
            {"Item": league_metadata_item},
            {"Item": {"stripe_customer_id": "cus_old"}},
        ]
        mock_table.put_item.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "InternalServerError", "Message": "x"}}, "PutItem"
        )
        with patch("main.stripe") as mock_stripe:
            mock_stripe.checkout.Session.create.side_effect = (
                stripe.error.InvalidRequestError("No such customer", "customer")
            )
            mock_stripe.Customer.create.return_value = {"id": "cus_new"}
            resp = client.post("/leagues/123/checkout-session?platform=SLEEPER")
        assert resp.status_code == 500

    def test_requires_authentication(
        self, client, mock_table, league_lookup_item, league_metadata_item
    ):
        # Drop the default auth override so the real dependency runs; with no
        # aws.event in scope it raises 401.
        import main
        import routes

        main.app.dependency_overrides.pop(routes.get_authenticated_user, None)
        resp = client.post("/leagues/123/checkout-session?platform=SLEEPER")
        assert resp.status_code == 401

    def test_returns_404_when_billing_disabled(self, client, override_user):
        # Billing feature-flagged off (BE-017): checkout is unreachable.
        from common import feature_flags

        feature_flags._override_for_testing({"billing": False})
        resp = client.post("/leagues/123/checkout-session?platform=SLEEPER")
        assert resp.status_code == 404


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

    def test_returns_404_when_billing_disabled(self, client, override_user):
        # Billing feature-flagged off (BE-017): the portal is unreachable, even
        # before any Stripe customer lookup.
        from common import feature_flags

        feature_flags._override_for_testing({"billing": False})
        resp = client.post("/billing-portal-session")
        assert resp.status_code == 404
