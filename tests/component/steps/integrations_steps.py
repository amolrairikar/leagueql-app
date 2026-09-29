"""Steps for community integrations (backend/integrations).

GitHub is replaced by ``FakeGitHub``, an in-memory issue store wired in at the
``integrations`` module's HTTP boundary (``requests.post`` for issue creation and the
retry session's ``get`` for listing), so the real routes, issue-body format, parsing,
and moto-backed submission limit all run.
"""

import os
import sys
from itertools import count
from unittest.mock import MagicMock, patch

from behave import given, then, when
from common_steps import get_item

APPROVED = "integration:approved"


class FakeGitHub:
    def __init__(self):
        self.issues: list[dict] = []
        self.reject_creates = False
        self._numbers = count(1)

    def _response(self, status: int, body=None) -> MagicMock:
        resp = MagicMock()
        resp.status_code = status
        resp.json.return_value = body
        resp.text = ""
        return resp

    def post(self, url, json=None, headers=None, timeout=None):
        if self.reject_creates:
            return self._response(500)
        number = next(self._numbers)
        self.issues.append(
            {
                "number": number,
                "title": json["title"],
                "body": json["body"],
                "labels": [{"name": name} for name in json["labels"]],
                # Monotonic per-issue timestamp so "newest" is well defined.
                "created_at": f"2026-09-28T00:00:{number:02d}Z",
            }
        )
        return self._response(201, {"number": number})

    def get(self, url, params=None, headers=None, timeout=None):
        wanted = params["labels"]
        matching = [
            issue
            for issue in self.issues
            if wanted in {label["name"] for label in issue["labels"]}
        ]
        return self._response(200, matching)

    def issue_titled(self, title: str) -> dict:
        return next(issue for issue in self.issues if issue["title"] == title)


def _integrations():
    return sys.modules["routes"].integrations


def _submission(name: str) -> dict:
    return {
        "name": name,
        "category": "bot",
        "link": "https://github.com/example/tool",
        "views": ["transactions", "matchups"],
        "description": f"{name} does something useful.",
        "setup_steps": ["Fork the repo.", "Run it."],
    }


def _start(context, patcher):
    patcher.start()
    context._patches.append(patcher)


@given("GitHub is reachable")
def step_github_reachable(context):
    integrations = _integrations()
    integrations._reset_for_testing()
    context.github = FakeGitHub()
    session = MagicMock()
    session.get.side_effect = context.github.get
    _start(context, patch.dict(os.environ, {"GITHUB_REPO": "owner/leagueql-app"}))
    _start(context, patch.object(integrations, "_github_token", return_value="tok"))
    _start(context, patch.object(integrations, "_get_session", return_value=session))
    _start(
        context,
        patch.object(integrations.requests, "post", side_effect=context.github.post),
    )


@given("GitHub rejects issue creation")
def step_github_rejects(context):
    context.github.reject_creates = True


@given('GitHub has an approved integration "{name}" labeled "{label}"')
def step_seed_approved(context, name, label):
    integrations = _integrations()
    submission = integrations.IntegrationSubmission(**_submission(name))
    context.github.post(
        None,
        json={
            "title": f"[Integration] {name}",
            "body": integrations.build_issue_body(submission),
            "labels": [APPROVED, label],
        },
    )


@when('I submit the integration "{name}"')
def step_submit(context, name):
    context.response = context.api.post("/integrations", json=_submission(name))


@when('the maintainer adds the "{label}" label to "{title}"')
def step_add_label(context, label, title):
    context.github.issue_titled(title)["labels"].append({"name": label})


@when("the integrations listing cache has expired")
def step_expire_cache(context):
    integrations = _integrations()
    integrations._cached_at = 0.0
    integrations._cached_items = None


@then('GitHub has an issue titled "{title}" labeled "{label}"')
def step_assert_issue(context, title, label):
    issue = context.github.issue_titled(title)
    assert label in {lbl["name"] for lbl in issue["labels"]}, issue["labels"]
    assert context.default_user not in issue["body"], "account id leaked into issue"


@then("GitHub has {n:d} issue(s)")
def step_assert_issue_count(context, n):
    assert len(context.github.issues) == n, context.github.issues


@then("the integrations listing has {n:d} item(s)")
def step_assert_listing_count(context, n):
    items = context.response.json()["data"]["items"]
    assert len(items) == n, items


@then('the integrations listing includes "{name}"')
def step_assert_listing_item(context, name):
    items = context.response.json()["data"]["items"]
    assert any(i["name"] == name for i in items), items


@then('only "{name}" is featured in the integrations listing')
def step_assert_featured(context, name):
    items = context.response.json()["data"]["items"]
    featured = [i["name"] for i in items if i["featured"]]
    assert featured == [name], featured


@then("the default user has {n:d} recorded integration submission(s)")
def step_assert_recorded(context, n):
    item = get_item(context, f"USER#{context.default_user}", "INTEGRATION_SUBMISSIONS")
    recorded = len(item["submitted_at"]) if item else 0
    assert recorded == n, item
