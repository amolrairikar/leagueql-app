"""Steps for the weekly recap backfill component (BE-022).

The webhook's async recap invoke is bridged to call the recap handler directly
(see environment.py); the AI path goes through a mocked Bedrock Converse client
that returns a fixed narrative. These steps assert the RECAP items the backfill
wrote (incl. the ``model`` that produced them), that re-firing doesn't regenerate
them (idempotency, via an unchanged ``generated_at``), and that a Bedrock outage
leaves the week un-recapped (no fallback).
"""

from behave import given, then

from common_steps import get_item


@given("the Bedrock recap model is unavailable")
def step_bedrock_unavailable(context):
    # Force every Converse call to fail so the orchestrator falls back to the
    # deterministic snippet composer. Reset per scenario in environment.py.
    context.recap_ai_generate._client.converse.side_effect = RuntimeError(
        "bedrock unavailable"
    )


def _recap_data(context, canonical, season, ww):
    item = get_item(context, f"LEAGUE#{canonical}", f"RECAP#{season}#WEEK#{ww}")
    assert item is not None, f"no RECAP item for {canonical} {season} week {ww}"
    data = item["data"]
    assert isinstance(data, list) and len(data) == 1, f"unexpected data shape: {data}"
    return data[0]


@then('a RECAP item exists for league "{canonical}" season "{season}" week "{ww}"')
def step_recap_exists(context, canonical, season, ww):
    recap = _recap_data(context, canonical, season, ww)
    assert recap["headline"], "recap headline is empty"
    assert recap["body"], "recap body is empty"


@then('no RECAP item exists for league "{canonical}" season "{season}" week "{ww}"')
def step_recap_absent(context, canonical, season, ww):
    item = get_item(context, f"LEAGUE#{canonical}", f"RECAP#{season}#WEEK#{ww}")
    assert item is None, f"unexpected RECAP item for {canonical} {season} week {ww}"


@then(
    'I remember the recap "generated_at" for league "{canonical}" '
    'season "{season}" week "{ww}"'
)
def step_remember_generated_at(context, canonical, season, ww):
    context.remembered_generated_at = _recap_data(context, canonical, season, ww)[
        "generated_at"
    ]


@then(
    'the recap "generated_at" for league "{canonical}" season "{season}" '
    'week "{ww}" is unchanged'
)
def step_generated_at_unchanged(context, canonical, season, ww):
    # A re-fired backfill must skip an already-written week (idempotent, no
    # regeneration) — the recap row, and so its generated_at, is untouched.
    current = _recap_data(context, canonical, season, ww)["generated_at"]
    assert current == context.remembered_generated_at, (
        f"recap regenerated: {context.remembered_generated_at!r} -> {current!r}"
    )


@then("the recap response headline is not empty")
def step_recap_headline_not_empty(context):
    data = context.response.json()["data"]
    assert data, "empty recap query response"
    assert data[0]["headline"], f"empty headline: {data[0]!r}"


@then(
    'the recap "model" for league "{canonical}" season "{season}" '
    'week "{ww}" is "{model}"'
)
def step_recap_model_is(context, canonical, season, ww, model):
    actual = _recap_data(context, canonical, season, ww)["model"]
    assert actual == model, f"expected model {model!r}, got {actual!r}"
