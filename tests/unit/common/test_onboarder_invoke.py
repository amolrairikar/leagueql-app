"""Tests for the shared src/common/onboarder_invoke.py module."""

import json
from unittest.mock import MagicMock

from common.onboarder_invoke import invoke_onboarder


def test_invoke_onboarder_builds_payload_and_invokes():
    client = MagicMock()
    client.invoke.return_value = {"StatusCode": 202}

    result = invoke_onboarder(
        lambda_client=client,
        function_name="onboarder-fn",
        body={"leagueId": "123", "platform": "SLEEPER"},
        request_type="REFRESH",
        canonical_league_id="canonical-abc",
        correlation_id="corr-1",
    )

    assert result == {"StatusCode": 202}
    client.invoke.assert_called_once()
    kwargs = client.invoke.call_args.kwargs
    assert kwargs["FunctionName"] == "onboarder-fn"
    assert kwargs["InvocationType"] == "Event"
    payload = json.loads(kwargs["Payload"])
    assert payload == {
        "body": {"leagueId": "123", "platform": "SLEEPER"},
        "requestType": "REFRESH",
        "canonicalLeagueId": "canonical-abc",
        "correlation_id": "corr-1",
    }


def test_invoke_onboarder_allows_none_canonical_id():
    client = MagicMock()
    invoke_onboarder(
        lambda_client=client,
        function_name="onboarder-fn",
        body={"leagueId": "123", "platform": "SLEEPER"},
        request_type="ONBOARD",
        canonical_league_id=None,
        correlation_id="corr-1",
    )
    payload = json.loads(client.invoke.call_args.kwargs["Payload"])
    assert payload["canonicalLeagueId"] is None
