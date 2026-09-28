"""Tests for the GitHub-backed integrations module (backend/integrations)."""

import os
from unittest.mock import MagicMock, patch

import integrations
import pytest
import requests
from integrations import (
    APPROVED_LABEL,
    BODY_MARKER,
    FEATURED_LABEL,
    SUBMITTED_LABEL,
    GitHubError,
    IntegrationSubmission,
    build_issue_body,
    create_issue,
    list_approved,
    parse_issue_body,
)
from pydantic import ValidationError


def _valid(**overrides) -> dict:
    data = {
        "name": "Trade Grader",
        "author_handle": "benchwarmer",
        "category": "bot",
        "link": "https://github.com/example/trade-grader",
        "views": ["transactions", "matchups"],
        "description": "Grades every trade the morning after the deadline.",
        "setup_steps": ["Fork the repo.", "Add your webhook secret."],
    }
    data.update(overrides)
    return data


def _submission(**overrides) -> IntegrationSubmission:
    return IntegrationSubmission(**_valid(**overrides))


def _response(status: int, json_body=None, text: str = "") -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = json_body
    resp.text = text
    return resp


def _issue(number: int, submission=None, labels=(APPROVED_LABEL,), **extra) -> dict:
    return {
        "number": number,
        "body": build_issue_body(submission or _submission(name=f"Tool {number}")),
        "labels": [{"name": name} for name in labels],
        "created_at": f"2026-09-{number:02d}T00:00:00Z",
        **extra,
    }


@pytest.fixture(autouse=True)
def _github_env():
    integrations._reset_for_testing()
    with (
        patch.dict(
            os.environ,
            {"GITHUB_REPO": "owner/repo", "GITHUB_TOKEN_SSM_PARAM": "/test/token"},
        ),
        patch.object(integrations, "get_secret_from_env_param", return_value="tok"),
    ):
        yield
    integrations._reset_for_testing()


class TestSubmissionModel:
    def test_valid_submission(self):
        sub = _submission(views=["matchups", "matchups", "teams"], prompt="")
        assert sub.category == "bot"
        assert sub.views == ["matchups", "teams"]
        assert sub.prompt is None

    def test_export_views_match_the_export(self):
        from main import EXPORT_SEASON_VIEWS

        assert set(integrations.ExportView.__args__) == set(EXPORT_SEASON_VIEWS) | {
            "teams"
        }

    @pytest.mark.parametrize(
        "overrides",
        [
            {"name": ""},
            {"name": "x" * 61},
            {"name": "has `backtick`"},
            {"name": "two\nlines"},
            {"author_handle": "x" * 31},
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
            {"setup_steps": ["step"] * 7},
            {"setup_steps": ["x" * 201]},
            {"setup_steps": ["line\nbreak"]},
            {"prompt": "x" * 2001},
            {"unexpected": "field"},
        ],
    )
    def test_invalid_submissions_rejected(self, overrides):
        with pytest.raises(ValidationError):
            _submission(**overrides)


class TestIssueBody:
    def test_round_trips_every_field(self):
        sub = _submission(
            category="ai_prompt",
            description="Line one.\nLine two with ### not a heading.",
            prompt="Read README.md first.\n```sql\nSELECT 1;\n```",
        )
        body = build_issue_body(sub)
        assert body.startswith(BODY_MARKER)
        assert parse_issue_body(body) == sub

    def test_round_trips_without_prompt(self):
        sub = _submission()
        body = build_issue_body(sub)
        assert "### Prompt" not in body
        assert parse_issue_body(body) == sub

    def test_mentions_and_markdown_are_neutralized(self):
        sub = _submission(
            name="Ping @octocat",
            description="cc @octocat **bold** [link](https://evil.example)",
        )
        body = build_issue_body(sub)
        assert "`Ping @octocat`" in body
        # The description sits inside a fenced block, so GitHub renders it literally.
        assert "```text\ncc @octocat **bold** [link](https://evil.example)\n```" in body

    def test_fence_outlasts_backticks_in_content(self):
        sub = _submission(description="Use ```` to fence.")
        body = build_issue_body(sub)
        assert "`````text\nUse ```` to fence.\n`````" in body
        assert parse_issue_body(body).description == "Use ```` to fence."

    def test_no_account_identifier_in_body(self):
        body = build_issue_body(_submission())
        assert "user_" not in body

    def test_accepts_maintainer_plain_text_edits(self):
        body = build_issue_body(_submission()).replace("`benchwarmer`", "bench_warmer")
        assert parse_issue_body(body).author_handle == "bench_warmer"

    @pytest.mark.parametrize("body", [None, "", "### Name\n\n`No marker`"])
    def test_missing_marker_returns_none(self, body):
        assert parse_issue_body(body) is None

    def test_invalid_field_returns_none(self):
        body = build_issue_body(_submission()).replace("`bot`", "`game`")
        assert parse_issue_body(body) is None

    def test_missing_section_returns_none(self):
        body = build_issue_body(_submission()).replace("### Link", "### Website")
        assert parse_issue_body(body) is None


class TestCreateIssue:
    def test_creates_labeled_issue(self):
        with patch.object(
            integrations.requests, "post", return_value=_response(201, {"number": 42})
        ) as post:
            assert create_issue(_submission()) == 42
        post.assert_called_once()
        url = post.call_args.args[0]
        kwargs = post.call_args.kwargs
        assert url == "https://api.github.com/repos/owner/repo/issues"
        assert kwargs["json"]["title"] == "[Integration] Trade Grader"
        assert kwargs["json"]["labels"] == [SUBMITTED_LABEL]
        assert kwargs["headers"]["Authorization"] == "Bearer tok"
        assert kwargs["json"]["body"] == build_issue_body(_submission())

    def test_non_201_raises_after_one_attempt(self):
        with (
            patch.object(
                integrations.requests, "post", return_value=_response(500, text="boom")
            ) as post,
            pytest.raises(GitHubError, match="500"),
        ):
            create_issue(_submission())
        assert post.call_count == 1

    def test_timeout_raises(self):
        with (
            patch.object(
                integrations.requests, "post", side_effect=requests.Timeout("slow")
            ) as post,
            pytest.raises(GitHubError),
        ):
            create_issue(_submission())
        assert post.call_count == 1

    def test_missing_repo_raises(self):
        with (
            patch.dict(os.environ, {"GITHUB_REPO": ""}),
            pytest.raises(GitHubError, match="GITHUB_REPO"),
        ):
            create_issue(_submission())

    def test_missing_token_raises(self):
        with (
            patch.object(integrations, "get_secret_from_env_param", return_value=""),
            patch.object(integrations.requests, "post") as post,
            pytest.raises(GitHubError, match="token"),
        ):
            create_issue(_submission())
        post.assert_not_called()

    def test_token_resolved_once(self):
        with (
            patch.object(
                integrations, "get_secret_from_env_param", return_value="tok"
            ) as secret,
            patch.object(
                integrations.requests,
                "post",
                return_value=_response(201, {"number": 1}),
            ),
        ):
            create_issue(_submission())
            create_issue(_submission())
        secret.assert_called_once_with("GITHUB_TOKEN_SSM_PARAM")


class TestListApproved:
    @pytest.fixture
    def session(self):
        session = MagicMock()
        with patch.object(integrations, "build_retry_session", return_value=session):
            yield session

    def test_lists_approved_issues_newest_first(self, session):
        session.get.return_value = _response(200, [_issue(1), _issue(3), _issue(2)])
        items = list_approved()
        assert [i["issue_number"] for i in items] == [3, 2, 1]
        assert items[0]["name"] == "Tool 3"
        assert items[0]["featured"] is False
        assert "_created_at" not in items[0]
        params = session.get.call_args.kwargs["params"]
        assert params["labels"] == APPROVED_LABEL
        assert params["state"] == "all"

    def test_skips_pull_requests_and_malformed_bodies(self, session):
        broken = _issue(4)
        broken["body"] = "edited away the marker"
        session.get.return_value = _response(
            200, [_issue(1), _issue(2, pull_request={}), broken, _issue(3)]
        )
        assert [i["issue_number"] for i in list_approved()] == [3, 1]

    def test_only_newest_featured(self, session):
        featured = (APPROVED_LABEL, FEATURED_LABEL)
        session.get.return_value = _response(
            200, [_issue(1, labels=featured), _issue(2, labels=featured), _issue(3)]
        )
        featured_flags = {i["issue_number"]: i["featured"] for i in list_approved()}
        assert featured_flags == {3: False, 2: True, 1: False}

    def test_served_from_cache_within_ttl(self, session):
        session.get.return_value = _response(200, [_issue(1)])
        list_approved()
        list_approved()
        assert session.get.call_count == 1

    def test_refetches_after_ttl(self, session):
        session.get.return_value = _response(200, [_issue(1)])
        with patch.object(integrations.time, "monotonic", side_effect=[1000.0, 1400.0]):
            list_approved()
            session.get.return_value = _response(200, [_issue(1), _issue(2)])
            assert len(list_approved()) == 2
        assert session.get.call_count == 2

    def test_serves_stale_listing_when_github_fails(self, session):
        session.get.return_value = _response(200, [_issue(1)])
        with patch.object(integrations.time, "monotonic", side_effect=[1000.0, 1400.0]):
            list_approved()
            session.get.return_value = _response(503)
            assert [i["issue_number"] for i in list_approved()] == [1]

    def test_raises_when_no_listing_ever_fetched(self, session):
        session.get.side_effect = requests.ConnectionError("down")
        with pytest.raises(GitHubError):
            list_approved()

    def test_non_200_without_cache_raises(self, session):
        session.get.return_value = _response(401)
        with pytest.raises(GitHubError, match="401"):
            list_approved()
