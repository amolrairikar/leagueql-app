"""Unit tests for the SNS-to-Discord alert forwarder Lambda."""

import json

import pytest
import requests


def _sns_event(message, subject=None):
    """Wrap a single SNS message in the Lambda event envelope."""
    return {"Records": [{"Sns": {"Subject": subject, "Message": message}}]}


def _posted_embed(mock_post):
    """Return the single embed dict from the most recent Discord POST."""
    return mock_post.call_args.kwargs["json"]["embeds"][0]


class TestCloudWatchAlarm:
    def test_alarm_state_renders_red_embed_with_fields(self, handler, mock_post):
        message = json.dumps(
            {
                "AlarmName": "leagueql-onboarder-prod-errors",
                "AlarmDescription": "Onboarder Lambda error detected",
                "NewStateValue": "ALARM",
                "NewStateReason": "Threshold crossed: 1 datapoint.",
                "Region": "US East (N. Virginia)",
            }
        )
        handler.lambda_handler(_sns_event(message), None)

        embed = _posted_embed(mock_post)
        assert embed["title"] == "leagueql-onboarder-prod-errors"
        assert embed["description"] == "Threshold crossed: 1 datapoint."
        assert embed["color"] == handler._COLOR_RED
        assert {"name": "State", "value": "ALARM", "inline": True} in embed["fields"]
        assert {
            "name": "Region",
            "value": "US East (N. Virginia)",
            "inline": True,
        } in embed["fields"]
        assert mock_post.call_args.args[0] == handler._WEBHOOK_URL

    def test_ok_state_renders_green_embed(self, handler, mock_post):
        message = json.dumps(
            {
                "AlarmName": "leagueql-onboarder-prod-errors",
                "AlarmDescription": "Onboarder Lambda error detected",
                "NewStateValue": "OK",
                "NewStateReason": "Threshold no longer crossed.",
            }
        )
        handler.lambda_handler(_sns_event(message), None)

        embed = _posted_embed(mock_post)
        assert embed["color"] == handler._COLOR_GREEN
        # No Region field when the alarm payload omits it.
        assert all(f["name"] != "Region" for f in embed["fields"])

    def test_falls_back_to_alarm_description_when_no_reason(self, handler, mock_post):
        message = json.dumps(
            {
                "AlarmName": "alarm",
                "AlarmDescription": "described",
                "NewStateValue": "ALARM",
            }
        )
        handler.lambda_handler(_sns_event(message), None)
        assert _posted_embed(mock_post)["description"] == "described"


class TestEventBridgeEvent:
    def test_fargate_task_failure_renders_detail(self, handler, mock_post):
        message = json.dumps(
            {
                "source": "aws.ecs",
                "detail-type": "ECS Task State Change",
                "detail": {"lastStatus": "STOPPED", "stopCode": "TaskFailedToStart"},
            }
        )
        handler.lambda_handler(_sns_event(message), None)

        embed = _posted_embed(mock_post)
        assert embed["title"] == "ECS Task State Change"
        assert embed["color"] == handler._COLOR_RED
        assert "TaskFailedToStart" in embed["description"]


class TestPlainTextAndFallbacks:
    def test_app_failure_uses_subject_and_body(self, handler, mock_post):
        body = "Correlation ID: abc-123\nError: boom"
        handler.lambda_handler(_sns_event(body, subject="LeagueQL API Failure"), None)

        embed = _posted_embed(mock_post)
        assert embed["title"] == "LeagueQL API Failure"
        assert embed["description"] == body
        assert embed["color"] == handler._COLOR_RED

    def test_plain_text_without_subject_uses_default_title(self, handler, mock_post):
        handler.lambda_handler(_sns_event("just a string"), None)
        assert _posted_embed(mock_post)["title"] == "LeagueQL Alert"

    def test_non_dict_json_is_forwarded_as_plain_text(self, handler, mock_post):
        # Valid JSON that isn't an object (e.g. a JSON array) → plain-text fallback.
        handler.lambda_handler(_sns_event("[1, 2, 3]", subject="Weird"), None)
        embed = _posted_embed(mock_post)
        assert embed["title"] == "Weird"
        assert embed["description"] == "[1, 2, 3]"

    def test_unrecognized_json_object_is_pretty_printed(self, handler, mock_post):
        handler.lambda_handler(_sns_event(json.dumps({"foo": "bar"})), None)
        description = _posted_embed(mock_post)["description"]
        assert '"foo": "bar"' in description


class TestTruncation:
    def test_long_description_is_truncated(self, handler, mock_post):
        body = "x" * (handler._DESCRIPTION_LIMIT + 100)
        handler.lambda_handler(_sns_event(body), None)
        description = _posted_embed(mock_post)["description"]
        assert len(description) == handler._DESCRIPTION_LIMIT
        assert description.endswith("…")


class TestDelivery:
    def test_multiple_records_each_posted(self, handler, mock_post):
        event = {
            "Records": [
                {"Sns": {"Subject": "one", "Message": "first"}},
                {"Sns": {"Subject": "two", "Message": "second"}},
            ]
        }
        handler.lambda_handler(event, None)
        assert mock_post.call_count == 2

    def test_empty_event_posts_nothing(self, handler, mock_post):
        handler.lambda_handler({}, None)
        mock_post.assert_not_called()

    def test_non_2xx_response_raises(self, handler, mock_post):
        mock_post.return_value.raise_for_status.side_effect = requests.HTTPError("500")
        with pytest.raises(requests.HTTPError):
            handler.lambda_handler(_sns_event("boom"), None)

    def test_raises_when_webhook_url_unset(self, handler, mock_post, monkeypatch):
        monkeypatch.setattr(handler, "_WEBHOOK_URL", "")
        with pytest.raises(RuntimeError, match="webhook URL is not configured"):
            handler.lambda_handler(_sns_event("boom"), None)
        mock_post.assert_not_called()
