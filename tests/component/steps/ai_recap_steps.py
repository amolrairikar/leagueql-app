"""Steps for the AI weekly recap backfill component (BE-022).

The webhook's async recap invoke is bridged to call the recap handler directly
(see environment.py); the Bedrock client is mocked there to return a fixed
narrative. These steps assert the RECAP items the backfill wrote and the Bedrock
call count (idempotency).
"""

from behave import given, then

from common_steps import get_item

# `given` is re-exported so the decorator import isn't flagged unused when only a
# subset of step kinds is defined here.
_ = given


@then('a RECAP item exists for league "{canonical}" season "{season}" week "{ww}"')
def step_recap_exists(context, canonical, season, ww):
    item = get_item(context, f"LEAGUE#{canonical}", f"RECAP#{season}#WEEK#{ww}")
    assert item is not None, f"no RECAP item for {canonical} {season} week {ww}"
    data = item["data"]
    assert isinstance(data, list) and len(data) == 1, f"unexpected data shape: {data}"
    assert data[0]["headline"], "recap headline is empty"
    assert data[0]["body"], "recap body is empty"


@then("the Bedrock client was called {count:d} time(s)")
def step_bedrock_call_count(context, count):
    actual = context.ai_recap_generate._client.converse.call_count
    assert actual == count, f"expected {count} Bedrock calls, got {actual}"


@then('the recap response headline is "{headline}"')
def step_recap_headline(context, headline):
    data = context.response.json()["data"]
    assert data, "empty recap query response"
    assert data[0]["headline"] == headline, f"got {data[0]['headline']!r}"
