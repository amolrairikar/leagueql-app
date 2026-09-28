"""Community integrations backed by GitHub issues (backend/integrations).

A submission from the Integrations page becomes a GitHub issue in the LeagueQL repo,
labeled ``integration:submitted`` for maintainer review. The maintainer approves an
integration by adding ``integration:approved`` (and optionally ``integration:featured``);
``list_approved`` reads those issues back and parses their structured body into the cards
the SPA renders. GitHub is the only store: there is no table of listings.

The issue body is issue-form shaped — a version marker followed by ``### <Field>``
sections — so it stays readable in GitHub, maintainer edits before approval flow through
to the page, and a future ``v2`` format can coexist. Every user-supplied value is written
inside an inline code span or a fenced block so it cannot @mention anyone, autolink, or
inject Markdown into the issue.

The token is a repo-scoped fine-grained PAT stored as a SecureString SSM parameter whose
*name* arrives via ``GITHUB_TOKEN_SSM_PARAM``; the repo (``owner/name``) via ``GITHUB_REPO``.
"""

import os
import re
import time
from enum import StrEnum
from typing import Annotated, Literal

import requests
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from common.http import build_retry_session
from common.logging_utils import logger
from common.secrets import get_secret_from_env_param

SUBMITTED_LABEL = "integration:submitted"
APPROVED_LABEL = "integration:approved"
FEATURED_LABEL = "integration:featured"

BODY_MARKER = "<!-- leagueql-integration:v1 -->"

# How long a fetched approved-listing is served before GitHub is asked again. Per Lambda
# container, so an approval can take up to this long to show in every region.
LISTING_TTL_SECONDS = 300

_GITHUB_API = "https://api.github.com"
_POST_TIMEOUT = (5, 10)
# Shorter per-attempt timeout for the retried GET so the worst case stays well under the
# API Gateway integration timeout.
_GET_TIMEOUT = (3, 5)

# The export's view names: the keys of ``main.EXPORT_SEASON_VIEWS`` plus ``teams`` (read
# separately and split per season). Duplicated here rather than imported to avoid a
# ``routes`` → ``integrations`` → ``main`` import cycle; a unit test keeps them in sync.
ExportView = Literal[
    "standings",
    "weekly_standings",
    "matchups",
    "draft",
    "transactions",
    "playoff_bracket",
    "league_settings",
    "teams",
]

# Single-line values go in inline code spans, so they may not contain backticks or
# line breaks (either would break out of the span).
_SINGLE_LINE = r"^[^`\r\n]+$"
# https only, with a host; no whitespace, backticks, or angle brackets.
_HTTPS_URL = r"^https://[A-Za-z0-9.-]+(?::\d{1,5})?(?:[/?#][^\s`<>]*)?$"


class IntegrationCategory(StrEnum):
    AI_PROMPT = "ai_prompt"
    DASHBOARD = "dashboard"
    SPREADSHEET = "spreadsheet"
    BOT = "bot"
    NOTEBOOK = "notebook"


SetupStep = Annotated[str, Field(min_length=1, max_length=500, pattern=_SINGLE_LINE)]


class IntegrationSubmission(BaseModel):
    """A user's integration submission; also the shape re-validated when parsing an issue."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=60, pattern=_SINGLE_LINE)
    category: IntegrationCategory
    link: str = Field(max_length=300, pattern=_HTTPS_URL)
    views: list[ExportView] = Field(min_length=1)
    description: str = Field(min_length=1, max_length=500)
    setup_steps: list[SetupStep] = Field(min_length=1, max_length=10)
    prompt: str | None = Field(default=None, max_length=2000)

    @field_validator("views")
    @classmethod
    def _dedupe_views(cls, views: list[str]) -> list[str]:
        return list(dict.fromkeys(views))

    @field_validator("prompt")
    @classmethod
    def _blank_prompt_is_none(cls, prompt: str | None) -> str | None:
        return prompt or None


class GitHubError(Exception):
    """GitHub rejected or failed a request (non-2xx, timeout, or network error)."""


# ---------------------------------------------------------------------------
# Issue body format
# ---------------------------------------------------------------------------

_FIELD_HEADINGS = {
    "name": "Name",
    "category": "Category",
    "link": "Link",
    "views": "Views",
    "description": "Description",
    "setup_steps": "Setup steps",
    "prompt": "Prompt",
}
_HEADING_TO_FIELD = {heading: field for field, heading in _FIELD_HEADINGS.items()}

_FENCED_RE = re.compile(r"^(`{3,})[^\n`]*\n(.*?)\n?\1\s*$", re.DOTALL)


def _code_span(value: str) -> str:
    return f"`{value}`"


def _fenced(value: str) -> str:
    # The fence must be longer than any backtick run inside the content, so the content
    # can never close it early.
    longest_run = max((len(run) for run in re.findall(r"`+", value)), default=0)
    fence = "`" * max(3, longest_run + 1)
    return f"{fence}text\n{value}\n{fence}"


def build_issue_body(submission: IntegrationSubmission) -> str:
    """Render a submission as the structured, mention-safe issue body."""
    sections = [
        BODY_MARKER,
        (
            "_Submitted from the LeagueQL Integrations page. Add the "
            f"`{APPROVED_LABEL}` label to list it._"
        ),
        f"### {_FIELD_HEADINGS['name']}\n\n{_code_span(submission.name)}",
        f"### {_FIELD_HEADINGS['category']}\n\n{_code_span(submission.category.value)}",
        f"### {_FIELD_HEADINGS['link']}\n\n{_code_span(submission.link)}",
        f"### {_FIELD_HEADINGS['views']}\n\n"
        + ", ".join(_code_span(v) for v in submission.views),
        f"### {_FIELD_HEADINGS['description']}\n\n{_fenced(submission.description)}",
        (
            f"### {_FIELD_HEADINGS['setup_steps']}\n\n"
            f"{_fenced(chr(10).join(submission.setup_steps))}"
        ),
    ]
    if submission.prompt:
        sections.append(
            f"### {_FIELD_HEADINGS['prompt']}\n\n{_fenced(submission.prompt)}"
        )
    return "\n\n".join(sections) + "\n"


def _split_sections(body: str) -> dict[str, str]:
    """Map each known ``### <Heading>`` to its raw section text.

    Headings inside fenced blocks are ignored so a description or prompt that happens to
    contain ``### Something`` can't split the section.
    """
    sections: dict[str, list[str]] = {}
    current: list[str] | None = None
    fence: str | None = None
    for line in body.splitlines():
        stripped = line.strip()
        fence_match = re.match(r"^(`{3,})", stripped)
        if fence is None and stripped.startswith("### "):
            field = _HEADING_TO_FIELD.get(stripped[4:].strip())
            current = sections.setdefault(field, []) if field else None
            continue
        if fence_match:
            if fence is None:
                fence = fence_match.group(1)
            elif stripped.rstrip("`") == "" and len(stripped) >= len(fence):
                fence = None
        if current is not None:
            current.append(line)
    return {field: "\n".join(lines).strip() for field, lines in sections.items()}


def _unwrap(text: str) -> str:
    """Strip the fenced-block or code-span wrapper written by ``build_issue_body``.

    Unwrapped text (e.g. a maintainer retyped the value plainly) is returned as-is.
    """
    fenced = _FENCED_RE.match(text)
    if fenced:
        return fenced.group(2)
    if len(text) >= 2 and text.startswith("`") and text.endswith("`"):
        return text[1:-1]
    return text


def parse_issue_body(body: str | None) -> IntegrationSubmission | None:
    """Parse an issue body back into a validated submission, or ``None`` if malformed."""
    if not body or BODY_MARKER not in body:
        return None
    sections = _split_sections(body)
    fields: dict[str, object] = {
        field: _unwrap(sections[field])
        for field in ("name", "category", "link", "description")
        if field in sections
    }
    if "views" in sections:
        fields["views"] = [
            _unwrap(part.strip())
            for part in sections["views"].split(",")
            if part.strip()
        ]
    if "setup_steps" in sections:
        fields["setup_steps"] = [
            line.strip()
            for line in _unwrap(sections["setup_steps"]).splitlines()
            if line.strip()
        ]
    if sections.get("prompt"):
        fields["prompt"] = _unwrap(sections["prompt"])
    try:
        return IntegrationSubmission(**fields)
    except ValidationError:
        return None


# ---------------------------------------------------------------------------
# GitHub client
# ---------------------------------------------------------------------------

_token: str | None = None
_session: requests.Session | None = None


def _github_token() -> str:
    """Resolve the PAT once per container (lazily, so cold starts that never touch
    integrations skip the SSM call)."""
    global _token
    if _token is None:
        _token = get_secret_from_env_param("GITHUB_TOKEN_SSM_PARAM")
    return _token


def _repo() -> str:
    repo = os.environ.get("GITHUB_REPO", "")
    if not repo:
        raise GitHubError("GITHUB_REPO is not configured")
    return repo


def _headers() -> dict[str, str]:
    token = _github_token()
    if not token:
        raise GitHubError("GitHub token is not configured")
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "leagueql-api",
    }


def _get_session() -> requests.Session:
    global _session
    if _session is None:
        _session = build_retry_session()
    return _session


def create_issue(submission: IntegrationSubmission) -> int:
    """Open the review issue for a submission and return its number.

    A single attempt with no retry: retrying after a timeout could create a duplicate
    issue, so a failure surfaces to the user, who can resubmit.

    Raises:
        GitHubError: GitHub returned a non-201 status or the request failed.
    """
    url = f"{_GITHUB_API}/repos/{_repo()}/issues"
    payload = {
        "title": f"[Integration] {submission.name}",
        "body": build_issue_body(submission),
        "labels": [SUBMITTED_LABEL],
    }
    try:
        response = requests.post(
            url, json=payload, headers=_headers(), timeout=_POST_TIMEOUT
        )
    except requests.RequestException as e:
        raise GitHubError(f"GitHub issue creation failed: {e}") from e
    if response.status_code != 201:
        raise GitHubError(
            f"GitHub issue creation returned {response.status_code}: "
            f"{response.text[:300]}"
        )
    return int(response.json()["number"])


def _to_item(issue: dict) -> dict | None:
    submission = parse_issue_body(issue.get("body"))
    if submission is None:
        logger.warning(
            "Skipping approved integration issue #%s: body is not in the "
            "integration format",
            issue.get("number"),
        )
        return None
    labels = {label.get("name") for label in issue.get("labels", [])}
    return {
        "issue_number": issue["number"],
        **submission.model_dump(mode="json"),
        "featured": FEATURED_LABEL in labels,
        "_created_at": issue.get("created_at", ""),
    }


def _fetch_approved() -> list[dict]:
    url = f"{_GITHUB_API}/repos/{_repo()}/issues"
    params = {
        "labels": APPROVED_LABEL,
        "state": "all",
        "per_page": 100,
        "sort": "created",
        "direction": "desc",
    }
    try:
        response = _get_session().get(
            url, params=params, headers=_headers(), timeout=_GET_TIMEOUT
        )
    except requests.RequestException as e:
        raise GitHubError(f"GitHub issue listing failed: {e}") from e
    if response.status_code != 200:
        raise GitHubError(f"GitHub issue listing returned {response.status_code}")

    items = [
        item
        for issue in response.json()
        # The issues endpoint also returns pull requests; they are never integrations.
        if "pull_request" not in issue and (item := _to_item(issue)) is not None
    ]
    items.sort(key=lambda item: item["_created_at"], reverse=True)
    # At most one featured item: the newest one carrying the featured label.
    seen_featured = False
    for item in items:
        del item["_created_at"]
        if item["featured"]:
            item["featured"] = not seen_featured
            seen_featured = True
    return items


_cached_items: list[dict] | None = None
_cached_at: float = 0.0


def list_approved() -> list[dict]:
    """Return approved integrations, newest first, cached for ``LISTING_TTL_SECONDS``.

    When GitHub fails, the last successfully fetched listing is served even if expired;
    only when nothing has ever been fetched does the error propagate.

    Raises:
        GitHubError: GitHub failed and there is no previously fetched listing.
    """
    global _cached_items, _cached_at
    now = time.monotonic()
    if _cached_items is not None and now - _cached_at < LISTING_TTL_SECONDS:
        return _cached_items
    try:
        items = _fetch_approved()
    except GitHubError:
        if _cached_items is not None:
            logger.warning(
                "GitHub listing failed; serving the stale integrations listing",
                exc_info=True,
            )
            return _cached_items
        raise
    _cached_items, _cached_at = items, now
    return items


def _reset_for_testing() -> None:
    """Clear the listing cache, token, and session between tests."""
    global _cached_items, _cached_at, _token, _session
    _cached_items, _cached_at, _token, _session = None, 0.0, None, None
