"""Tests for the GitHub-backed integrations module (backend/integrations).

``integrations`` is imported inside fixtures, never at module level: collection runs
before the session fixture that imports ``main`` with boto3 patched, and importing it
earlier would build a real SSM client in ``common.secrets``.
"""

import os
from unittest.mock import MagicMock, patch

import pytest
import requests
from pydantic import ValidationError


def _valid(**overrides) -> dict:
    data = {
        "name": "Trade Grader",
        "category": "bot",
        "link": "https://github.com/example/trade-grader",
        "views": ["transactions", "matchups"],
        "description": "Grades every trade the morning after the deadline.",
        "setup_steps": ["Fork the repo.", "Add your webhook secret."],
    }
    data.update(overrides)
    return data


def _response(status: int, json_body=None, text: str = "") -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = json_body
    resp.text = text
    return resp


@pytest.fixture
def integ():
    import integrations

    return integrations


@pytest.fixture
def submission(integ):
    """Factory for a valid ``IntegrationSubmission`` with field overrides."""

    def make(**overrides):
        return integ.IntegrationSubmission(**_valid(**overrides))

    return make


@pytest.fixture
def issue(integ, submission):
    """Factory for a GitHub issue payload carrying a structured integration body."""

    def make(number: int, sub=None, labels=None, **extra) -> dict:
        labels = labels or (integ.APPROVED_LABEL,)
        return {
            "number": number,
            "body": integ.build_issue_body(sub or submission(name=f"Tool {number}")),
            "labels": [{"name": name} for name in labels],
            "created_at": f"2026-09-{number:02d}T00:00:00Z",
            **extra,
        }

    return make


@pytest.fixture(autouse=True)
def _github_env(integ):
    integ._reset_for_testing()
    with (
        patch.dict(
            os.environ,
            {"GITHUB_REPO": "owner/repo", "GITHUB_TOKEN_SSM_PARAM": "/test/token"},
        ),
        patch.object(integ, "get_secret_from_env_param", return_value="tok"),
    ):
        yield
    integ._reset_for_testing()


class TestSubmissionModel:
    def test_valid_submission(self, submission):
        sub = submission(views=["matchups", "matchups", "teams"], prompt="")
        assert sub.category == "bot"
        assert sub.views == ["matchups", "teams"]
        assert sub.prompt is None

    def test_accepts_max_setup_steps(self, submission):
        sub = submission(setup_steps=["x" * 500] * 10)
        assert len(sub.setup_steps) == 10

    def test_export_views_match_the_export(self, integ):
        from main import EXPORT_SEASON_VIEWS

        assert set(integ.ExportView.__args__) == set(EXPORT_SEASON_VIEWS) | {"teams"}

    @pytest.mark.parametrize(
        "overrides",
        [
            {"name": ""},
            {"name": "x" * 61},
            {"name": "has `backtick`"},
            {"name": "two\nlines"},
            {"category": "game"},
            {"link": "http://example.com"},
            {"link": "javascript:alert(1)"},
            {"link": "https://"},
            {"link": "https://example.com/" + "a" * 300},
            {"link": "https://example.com/`x`"},
            {"views": []},
            {"views": ["secret_view"]},
            {"description": ""},
            {"description": "x" * 501},
            {"setup_steps": []},
            {"setup_steps": ["step"] * 11},
            {"setup_steps": ["x" * 501]},
            {"setup_steps": ["line\nbreak"]},
            {"prompt": "x" * 2001},
            {"unexpected": "field"},
        ],
    )
    def test_invalid_submissions_rejected(self, submission, overrides):
        with pytest.raises(ValidationError):
            submission(**overrides)


class TestIssueBody:
    def test_round_trips_every_field(self, integ, submission):
        sub = submission(
            category="ai_prompt",
            description="Line one.\nLine two with ### not a heading.",
            prompt="Read README.md first.\n```sql\nSELECT 1;\n```",
        )
        body = integ.build_issue_body(sub)
        assert body.startswith(integ.BODY_MARKER)
        assert integ.parse_issue_body(body) == sub

    def test_round_trips_without_prompt(self, integ, submission):
        sub = submission()
        body = integ.build_issue_body(sub)
        assert "### Prompt" not in body
        assert integ.parse_issue_body(body) == sub

    def test_mentions_and_markdown_are_neutralized(self, integ, submission):
        sub = submission(
            name="Ping @octocat",
            description="cc @octocat **bold** [link](https://evil.example)",
        )
        body = integ.build_issue_body(sub)
        assert "`Ping @octocat`" in body
        # The description sits inside a fenced block, so GitHub renders it literally.
        assert "```text\ncc @octocat **bold** [link](https://evil.example)\n```" in body

    def test_fence_outlasts_backticks_in_content(self, integ, submission):
        sub = submission(description="Use ```` to fence.")
        body = integ.build_issue_body(sub)
        assert "`````text\nUse ```` to fence.\n`````" in body
        assert integ.parse_issue_body(body).description == "Use ```` to fence."

    def test_no_account_identifier_in_body(self, integ, submission):
        body = integ.build_issue_body(submission())
        assert "user_" not in body

    def test_accepts_maintainer_plain_text_edits(self, integ, submission):
        body = integ.build_issue_body(submission()).replace(
            "`Trade Grader`", "Trade Grader 2"
        )
        assert integ.parse_issue_body(body).name == "Trade Grader 2"

    def test_ignores_unknown_sections(self, integ, submission):
        body = integ.build_issue_body(submission()).replace(
            "### Category", "### Author\n\n`benchwarmer`\n\n### Category"
        )
        assert integ.parse_issue_body(body) == submission()

    @pytest.mark.parametrize("body", [None, "", "### Name\n\n`No marker`"])
    def test_missing_marker_returns_none(self, integ, body):
        assert integ.parse_issue_body(body) is None

    def test_invalid_field_returns_none(self, integ, submission):
        body = integ.build_issue_body(submission()).replace("`bot`", "`game`")
        assert integ.parse_issue_body(body) is None

    def test_missing_section_returns_none(self, integ, submission):
        body = integ.build_issue_body(submission()).replace("### Link", "### Website")
        assert integ.parse_issue_body(body) is None


class TestCreateIssue:
    def test_creates_labeled_issue(self, integ, submission):
        with patch.object(
            integ.requests, "post", return_value=_response(201, {"number": 42})
        ) as post:
            assert integ.create_issue(submission()) == 42
        post.assert_called_once()
        url = post.call_args.args[0]
        kwargs = post.call_args.kwargs
        assert url == "https://api.github.com/repos/owner/repo/issues"
        assert kwargs["json"]["title"] == "[Integration] Trade Grader"
        assert kwargs["json"]["labels"] == [integ.SUBMITTED_LABEL]
        assert kwargs["headers"]["Authorization"] == "Bearer tok"
        assert kwargs["json"]["body"] == integ.build_issue_body(submission())

    def test_non_201_raises_after_one_attempt(self, integ, submission):
        with (
            patch.object(
                integ.requests, "post", return_value=_response(500, text="boom")
            ) as post,
            pytest.raises(integ.GitHubError, match="500"),
        ):
            integ.create_issue(submission())
        assert post.call_count == 1

    def test_timeout_raises(self, integ, submission):
        with (
            patch.object(
                integ.requests, "post", side_effect=requests.Timeout("slow")
            ) as post,
            pytest.raises(integ.GitHubError),
        ):
            integ.create_issue(submission())
        assert post.call_count == 1

    def test_missing_repo_raises(self, integ, submission):
        with (
            patch.dict(os.environ, {"GITHUB_REPO": ""}),
            pytest.raises(integ.GitHubError, match="GITHUB_REPO"),
        ):
            integ.create_issue(submission())

    def test_missing_token_raises(self, integ, submission):
        with (
            patch.object(integ, "get_secret_from_env_param", return_value=""),
            patch.object(integ.requests, "post") as post,
            pytest.raises(integ.GitHubError, match="token"),
        ):
            integ.create_issue(submission())
        post.assert_not_called()

    def test_token_resolved_once(self, integ, submission):
        with (
            patch.object(
                integ, "get_secret_from_env_param", return_value="tok"
            ) as secret,
            patch.object(
                integ.requests, "post", return_value=_response(201, {"number": 1})
            ),
        ):
            integ.create_issue(submission())
            integ.create_issue(submission())
        secret.assert_called_once_with("GITHUB_TOKEN_SSM_PARAM")


class TestListApproved:
    @pytest.fixture
    def session(self, integ):
        session = MagicMock()
        with patch.object(integ, "build_retry_session", return_value=session):
            yield session

    def test_lists_approved_issues_newest_first(self, integ, issue, session):
        session.get.return_value = _response(200, [issue(1), issue(3), issue(2)])
        items = integ.list_approved()
        assert [i["issue_number"] for i in items] == [3, 2, 1]
        assert items[0]["name"] == "Tool 3"
        assert items[0]["featured"] is False
        assert "_created_at" not in items[0]
        params = session.get.call_args.kwargs["params"]
        assert params["labels"] == integ.APPROVED_LABEL
        assert params["state"] == "all"

    def test_skips_pull_requests_and_malformed_bodies(self, integ, issue, session):
        broken = issue(4)
        broken["body"] = "edited away the marker"
        session.get.return_value = _response(
            200, [issue(1), issue(2, pull_request={}), broken, issue(3)]
        )
        assert [i["issue_number"] for i in integ.list_approved()] == [3, 1]

    def test_only_newest_featured(self, integ, issue, session):
        featured = (integ.APPROVED_LABEL, integ.FEATURED_LABEL)
        session.get.return_value = _response(
            200, [issue(1, labels=featured), issue(2, labels=featured), issue(3)]
        )
        flags = {i["issue_number"]: i["featured"] for i in integ.list_approved()}
        assert flags == {3: False, 2: True, 1: False}

    def test_served_from_cache_within_ttl(self, integ, issue, session):
        session.get.return_value = _response(200, [issue(1)])
        integ.list_approved()
        integ.list_approved()
        assert session.get.call_count == 1

    def test_refetches_after_ttl(self, integ, issue, session):
        session.get.return_value = _response(200, [issue(1)])
        with patch.object(integ.time, "monotonic", side_effect=[1000.0, 1400.0]):
            integ.list_approved()
            session.get.return_value = _response(200, [issue(1), issue(2)])
            assert len(integ.list_approved()) == 2
        assert session.get.call_count == 2

    def test_serves_stale_listing_when_github_fails(self, integ, issue, session):
        session.get.return_value = _response(200, [issue(1)])
        with patch.object(integ.time, "monotonic", side_effect=[1000.0, 1400.0]):
            integ.list_approved()
            session.get.return_value = _response(503)
            assert [i["issue_number"] for i in integ.list_approved()] == [1]

    def test_raises_when_no_listing_ever_fetched(self, integ, session):
        session.get.side_effect = requests.ConnectionError("down")
        with pytest.raises(integ.GitHubError):
            integ.list_approved()

    def test_non_200_without_cache_raises(self, integ, session):
        session.get.return_value = _response(401)
        with pytest.raises(integ.GitHubError, match="401"):
            integ.list_approved()
