"""Steps for the nightly admin onboarding report Lambda (backend/admin-onboarding-report)."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from behave import given, then, when
from common_steps import put_item


def _seed_metadata(context, cid, platform, onboarded_days, accessed_days, active=None):
    """Seed a METADATA item indexed by GSI3 (carries ``onboarded_at``)."""
    now = datetime.now(timezone.utc)
    item = {
        "PK": f"LEAGUE#{cid}",
        "SK": "METADATA",
        "platform": platform,
        "league_name": "Test League",
        "onboarded_at": (now - timedelta(days=onboarded_days)).isoformat(),
    }
    if active is not None:
        item["active_platform"] = active
    if accessed_days is not None:
        item["last_accessed_at"] = (now - timedelta(days=accessed_days)).isoformat()
    put_item(context, item)


@given(
    'an onboarded league "{cid}" platform "{platform}" onboarded {odays:d} days ago, '
    "last accessed {adays:d} days ago"
)
def step_seed_active(context, cid, platform, odays, adays):
    _seed_metadata(context, cid, platform, odays, adays)


@given(
    'an onboarded league "{cid}" migrated to "{active}" onboarded {odays:d} days ago, '
    "never accessed"
)
def step_seed_migrated_never_accessed(context, cid, active, odays):
    # Original platform ESPN, now active on the migration target (backend/league-migration).
    _seed_metadata(context, cid, "ESPN", odays, accessed_days=None, active=active)


@when("the nightly onboarding report runs")
def step_run_report(context):
    handler = context.admin_report_handler
    post = MagicMock()
    post.return_value.status_code = 204
    post.return_value.raise_for_status.return_value = None
    post_patch = patch.object(handler._session, "post", post)
    post_patch.start()
    context._patches.append(post_patch)

    handler.lambda_handler({}, MagicMock())
    context.report_embed = post.call_args.kwargs["json"]["embeds"][0]


def _field(context, name):
    for field in context.report_embed["fields"]:
        if field["name"] == name:
            return field["value"]
    raise AssertionError(f"field {name!r} not in embed: {context.report_embed}")


@then('the report field "{name}" is "{value}"')
def step_field_equals(context, name, value):
    actual = _field(context, name)
    assert actual == value, f"field {name!r}: expected {value!r}, got {actual!r}"


@then('the report "{name}" field contains "{fragment}"')
def step_field_contains(context, name, fragment):
    actual = _field(context, name)
    assert fragment in actual, f"field {name!r}: {fragment!r} not in {actual!r}"
