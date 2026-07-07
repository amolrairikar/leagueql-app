"""Unit tests for the Stripe webhook Lambda (BE-015)."""

import base64
import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest

# A far-future unix timestamp used for period/trial ends.
_FUTURE_TS = 1893456000  # 2030-01-01T00:00:00Z


def _event(body="{}", signature="sig", is_base64=False):
    return {
        "body": body,
        "headers": {"Stripe-Signature": signature},
        "isBase64Encoded": is_base64,
    }


def _stripe_event(event_type, obj, event_id="evt_1"):
    return {"id": event_id, "type": event_type, "data": {"object": obj}}


@pytest.fixture
def patched(webhook_handler):
    """Patch the handler's Stripe client, DynamoDB client, and write helpers."""
    wh = webhook_handler
    with (
        patch.object(wh, "stripe") as mock_stripe,
        patch.object(wh, "_dynamodb") as mock_ddb,
        patch.object(wh, "record_active_subscription") as mock_record,
        patch.object(wh, "expire_subscription") as mock_expire,
    ):
        mock_ddb.get_item.return_value = {}  # default: event not yet processed
        yield SimpleNamespace(
            wh=wh,
            stripe=mock_stripe,
            ddb=mock_ddb,
            record=mock_record,
            expire=mock_expire,
        )


class TestBillingDisabled:
    def test_returns_200_noop_when_billing_disabled(self, patched):
        # Billing feature-flagged off (BE-017): acknowledge the delivery with 200
        # without verifying the signature or writing any subscription state.
        from common import feature_flags

        feature_flags._override_for_testing({"billing": False})
        resp = patched.wh.lambda_handler(_event(), None)
        assert resp["statusCode"] == 200
        patched.stripe.Webhook.construct_event.assert_not_called()
        patched.record.assert_not_called()
        patched.expire.assert_not_called()
        patched.ddb.put_item.assert_not_called()


class TestSignatureVerification:
    def test_invalid_signature_returns_400(self, patched):
        patched.stripe.Webhook.construct_event.side_effect = ValueError("bad")
        resp = patched.wh.lambda_handler(_event(), None)
        assert resp["statusCode"] == 400
        patched.record.assert_not_called()
        patched.ddb.put_item.assert_not_called()

    def test_base64_body_is_decoded_before_verification(self, patched):
        patched.stripe.Webhook.construct_event.return_value = _stripe_event(
            "unhandled.event", {}
        )
        encoded = base64.b64encode(b'{"hello":1}').decode()
        patched.wh.lambda_handler(_event(body=encoded, is_base64=True), None)
        args, _ = patched.stripe.Webhook.construct_event.call_args
        assert args[0] == b'{"hello":1}'


class TestDedup:
    def test_already_processed_skips(self, patched):
        patched.stripe.Webhook.construct_event.return_value = _stripe_event(
            "checkout.session.completed", {"subscription": "sub_1"}
        )
        patched.ddb.get_item.return_value = {"Item": {"PK": "WEBHOOK_EVENT#evt_1"}}
        resp = patched.wh.lambda_handler(_event(), None)
        assert resp["statusCode"] == 200
        patched.stripe.Subscription.retrieve.assert_not_called()
        patched.record.assert_not_called()
        patched.ddb.put_item.assert_not_called()

    def test_records_dedup_marker_after_success(self, patched):
        patched.stripe.Webhook.construct_event.return_value = _stripe_event(
            "unhandled.event", {}
        )
        patched.wh.lambda_handler(_event(), None)
        patched.ddb.put_item.assert_called_once()
        _, kwargs = patched.ddb.put_item.call_args
        assert kwargs["Item"]["PK"] == {"S": "WEBHOOK_EVENT#evt_1"}
        assert "ttl" in kwargs["Item"]


class TestActivatingEvents:
    def test_active_subscription_records(self, patched):
        patched.stripe.Webhook.construct_event.return_value = _stripe_event(
            "checkout.session.completed", {"subscription": "sub_1"}
        )
        patched.stripe.Subscription.retrieve.return_value = {
            "status": "active",
            "current_period_end": _FUTURE_TS,
            "metadata": {"canonical_league_id": "cid"},
        }
        resp = patched.wh.lambda_handler(_event(), None)
        assert resp["statusCode"] == 200
        patched.record.assert_called_once()
        args, kwargs = patched.record.call_args
        assert args[0] == "cid"
        assert args[2] == "sub_1"
        assert kwargs["mark_trial_used"] is False
        patched.ddb.put_item.assert_called_once()

    def test_trialing_subscription_marks_trial_used(self, patched):
        patched.stripe.Webhook.construct_event.return_value = _stripe_event(
            "customer.subscription.created", {"id": "sub_1"}
        )
        patched.stripe.Subscription.retrieve.return_value = {
            "status": "trialing",
            "trial_end": _FUTURE_TS,
            "metadata": {
                "canonical_league_id": "cid",
                "platform": "SLEEPER",
                "native_league_id": "123",
            },
        }
        patched.wh.lambda_handler(_event(), None)
        _, kwargs = patched.record.call_args
        assert kwargs["mark_trial_used"] is True
        # Native identity is forwarded for the durable trial marker.
        assert kwargs["platform"] == "SLEEPER"
        assert kwargs["native_league_id"] == "123"

    def test_passes_none_native_identity_when_metadata_absent(self, patched):
        # Older subscriptions created before native IDs were added to metadata.
        patched.stripe.Webhook.construct_event.return_value = _stripe_event(
            "customer.subscription.created", {"id": "sub_1"}
        )
        patched.stripe.Subscription.retrieve.return_value = {
            "status": "trialing",
            "trial_end": _FUTURE_TS,
            "metadata": {"canonical_league_id": "cid"},
        }
        patched.wh.lambda_handler(_event(), None)
        _, kwargs = patched.record.call_args
        assert kwargs["platform"] is None
        assert kwargs["native_league_id"] is None

    def test_invoice_paid_uses_current_period_end(self, patched):
        patched.stripe.Webhook.construct_event.return_value = _stripe_event(
            "invoice.paid", {"subscription": "sub_1"}
        )
        patched.stripe.Subscription.retrieve.return_value = {
            "status": "active",
            "current_period_end": _FUTURE_TS,
            "metadata": {"canonical_league_id": "cid"},
        }
        patched.wh.lambda_handler(_event(), None)
        patched.record.assert_called_once()

    def test_duplicate_subscription_is_canceled(self, patched):
        patched.stripe.Webhook.construct_event.return_value = _stripe_event(
            "customer.subscription.created", {"id": "sub_dup"}
        )
        patched.stripe.Subscription.retrieve.return_value = {
            "status": "active",
            "current_period_end": _FUTURE_TS,
            "metadata": {"canonical_league_id": "cid"},
        }
        patched.record.side_effect = patched.wh.DuplicateSubscription("dup")
        resp = patched.wh.lambda_handler(_event(), None)
        assert resp["statusCode"] == 200
        patched.stripe.Subscription.cancel.assert_called_once_with("sub_dup")

    def test_invoice_without_subscription_skips(self, patched):
        patched.stripe.Webhook.construct_event.return_value = _stripe_event(
            "invoice.paid", {"subscription": None}
        )
        patched.wh.lambda_handler(_event(), None)
        patched.stripe.Subscription.retrieve.assert_not_called()
        patched.record.assert_not_called()

    def test_missing_canonical_id_skips(self, patched):
        patched.stripe.Webhook.construct_event.return_value = _stripe_event(
            "customer.subscription.created", {"id": "sub_1"}
        )
        patched.stripe.Subscription.retrieve.return_value = {
            "status": "active",
            "current_period_end": _FUTURE_TS,
            "metadata": {},
        }
        patched.wh.lambda_handler(_event(), None)
        patched.record.assert_not_called()

    def test_active_without_end_time_skips(self, patched):
        patched.stripe.Webhook.construct_event.return_value = _stripe_event(
            "customer.subscription.updated", {"id": "sub_1"}
        )
        patched.stripe.Subscription.retrieve.return_value = {
            "status": "active",
            "metadata": {"canonical_league_id": "cid"},
        }
        patched.wh.lambda_handler(_event(), None)
        patched.record.assert_not_called()

    def test_terminal_status_expires(self, patched):
        patched.stripe.Webhook.construct_event.return_value = _stripe_event(
            "customer.subscription.updated", {"id": "sub_1"}
        )
        patched.stripe.Subscription.retrieve.return_value = {
            "status": "canceled",
            "metadata": {"canonical_league_id": "cid"},
        }
        patched.wh.lambda_handler(_event(), None)
        patched.expire.assert_called_once_with("cid", "sub_1")

    def test_other_status_no_change(self, patched):
        patched.stripe.Webhook.construct_event.return_value = _stripe_event(
            "customer.subscription.updated", {"id": "sub_1"}
        )
        patched.stripe.Subscription.retrieve.return_value = {
            "status": "incomplete",
            "metadata": {"canonical_league_id": "cid"},
        }
        patched.wh.lambda_handler(_event(), None)
        patched.record.assert_not_called()
        patched.expire.assert_not_called()


class TestDeletedEvent:
    def test_deleted_expires_scoped_to_subscription(self, patched):
        patched.stripe.Webhook.construct_event.return_value = _stripe_event(
            "customer.subscription.deleted",
            {"id": "sub_1", "metadata": {"canonical_league_id": "cid"}},
        )
        patched.wh.lambda_handler(_event(), None)
        patched.expire.assert_called_once_with("cid", "sub_1")
        patched.stripe.Subscription.retrieve.assert_not_called()

    def test_deleted_without_canonical_id_skips(self, patched):
        patched.stripe.Webhook.construct_event.return_value = _stripe_event(
            "customer.subscription.deleted", {"id": "sub_1", "metadata": {}}
        )
        patched.wh.lambda_handler(_event(), None)
        patched.expire.assert_not_called()


class TestProcessingFailure:
    def test_processing_error_returns_500_and_not_recorded(self, patched):
        patched.stripe.Webhook.construct_event.return_value = _stripe_event(
            "checkout.session.completed", {"subscription": "sub_1"}
        )
        patched.stripe.Subscription.retrieve.return_value = {
            "status": "active",
            "current_period_end": _FUTURE_TS,
            "metadata": {"canonical_league_id": "cid"},
        }
        patched.record.side_effect = RuntimeError("boom")
        resp = patched.wh.lambda_handler(_event(), None)
        assert resp["statusCode"] == 500
        patched.ddb.put_item.assert_not_called()


class TestRecapTrigger:
    """The webhook launches the recap task only on a real activation (BE-021)."""

    def _active_event(self, patched):
        patched.stripe.Webhook.construct_event.return_value = _stripe_event(
            "checkout.session.completed", {"subscription": "sub_1"}
        )
        patched.stripe.Subscription.retrieve.return_value = {
            "status": "active",
            "current_period_end": _FUTURE_TS,
            "metadata": {
                "canonical_league_id": "cid",
                "platform": "ESPN",
                "native_league_id": "999",
            },
        }

    def test_enqueues_recap_when_subscription_advances(self, patched):
        self._active_event(patched)
        patched.record.return_value = True  # a real advance
        with patch.object(patched.wh, "record_pending_recap") as enqueue:
            resp = patched.wh.lambda_handler(_event(), None)
        assert resp["statusCode"] == 200
        enqueue.assert_called_once_with(
            canonical_league_id="cid",
            platform="ESPN",
            native_league_id="999",
            correlation_id="",
        )

    def test_does_not_fire_when_subscription_is_noop(self, patched):
        self._active_event(patched)
        patched.record.return_value = False  # stale/duplicate, non-advancing
        with patch.object(patched.wh, "record_pending_recap") as enqueue:
            resp = patched.wh.lambda_handler(_event(), None)
        assert resp["statusCode"] == 200
        enqueue.assert_not_called()

    def test_does_not_fire_for_integration_test_subscription(self, patched):
        # CI lifecycle subscriptions advance state (so subscription_end_time still
        # converges) but carry an integration_test marker, so the recap enqueue is
        # skipped — no Bedrock spend on the shared dev league (BE-021).
        self._active_event(patched)
        patched.stripe.Subscription.retrieve.return_value["metadata"][
            "integration_test"
        ] = "leagueql-stripe-lifecycle"
        patched.record.return_value = True  # a real advance
        with patch.object(patched.wh, "record_pending_recap") as enqueue:
            resp = patched.wh.lambda_handler(_event(), None)
        assert resp["statusCode"] == 200
        enqueue.assert_not_called()


class TestTracing:
    """The webhook is a traced Lambda starting a root span (BE-020)."""

    def test_lambda_handler_wraps_in_root_span(self, webhook_handler):
        with (
            patch.object(
                webhook_handler, "_handle", return_value={"statusCode": 200}
            ) as impl,
            patch.object(webhook_handler, "traced_handler") as th,
        ):
            result = webhook_handler.lambda_handler(_event(), None)
        assert result == {"statusCode": 200}
        th.assert_called_once_with("stripe_webhook.handle", root=True)
        impl.assert_called_once()

    def test_returns_200_with_tracing_unconfigured(self, patched):
        # The real (no-op) traced_handler is used here; behavior is unchanged.
        patched.stripe.Webhook.construct_event.return_value = _stripe_event(
            "unhandled.event", {}
        )
        resp = patched.wh.lambda_handler(_event(), None)
        assert resp["statusCode"] == 200


class TestHelpers:
    def test_current_period_end_falls_back_to_items(self, webhook_handler):
        sub = {"items": {"data": [{"current_period_end": _FUTURE_TS}]}}
        assert webhook_handler._current_period_end(sub) == _FUTURE_TS

    def test_current_period_end_none_when_absent(self, webhook_handler):
        assert webhook_handler._current_period_end({"items": {"data": []}}) is None

    def test_response_shape(self, webhook_handler):
        resp = webhook_handler._response(200, "OK")
        assert resp["statusCode"] == 200
        assert json.loads(resp["body"]) == {"detail": "OK"}
