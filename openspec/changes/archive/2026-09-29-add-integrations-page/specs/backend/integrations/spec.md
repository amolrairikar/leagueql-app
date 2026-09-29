# Spec Delta

## Purpose

Let signed-in users submit tools they built on LeagueQL's league export for maintainer review as GitHub issues, and
list the integrations the maintainer has approved so the frontend can showcase them.

## ADDED Requirements

### Requirement: Gate integrations endpoints behind a feature flag
`GET /integrations` and `POST /integrations` SHALL return `404` when the `integrations` feature flag is off, and the
flag SHALL be exposed in the `GET /feature-flags` payload as `integrations`.

#### Scenario: Flag off hides the endpoints
- **WHEN** the `integrations` flag is off and an authenticated user calls `GET /integrations` or `POST /integrations`
- **THEN** the API returns `404` and no GitHub request is made

#### Scenario: Flag exposed to the SPA
- **WHEN** the SPA calls `GET /feature-flags`
- **THEN** `data` contains an `integrations` boolean reflecting the flag's current value

### Requirement: Require authentication
Both integrations endpoints SHALL require a valid signed-in user and SHALL reject unauthenticated requests with
`401`.

#### Scenario: Unauthenticated request
- **WHEN** a request to `GET /integrations` or `POST /integrations` has no verified user identity
- **THEN** the API returns `401`

### Requirement: Validate integration submissions
`POST /integrations` SHALL accept a JSON body with `name` (1–60 chars), `category`
(one of `ai_prompt`, `dashboard`, `spreadsheet`, `bot`, `notebook`), `link` (an `https://` URL, ≤ 300 chars),
`views` (a non-empty list drawn only from the export's view names: `standings`, `weekly_standings`, `matchups`,
`draft`, `transactions`, `playoff_bracket`, `league_settings`, `teams`), `description` (1–500 chars),
`setup_steps` (1–10 items, each 1–500 chars), and optional `prompt` (≤ 2000 chars), and SHALL reject any other shape
with `422` without contacting GitHub.

#### Scenario: Invalid link scheme
- **WHEN** a submission's `link` is `http://example.com` or `javascript:alert(1)`
- **THEN** the API returns `422` and no issue is created

#### Scenario: Unknown view
- **WHEN** a submission's `views` contains `secret_view`
- **THEN** the API returns `422` and no issue is created

#### Scenario: Valid submission accepted
- **WHEN** a submission satisfies every field constraint
- **THEN** validation passes and the request proceeds to the submission limit check

### Requirement: Limit submissions per user
The API SHALL allow each user at most 3 accepted submissions per rolling 24 hours and SHALL reject further
submissions with `429` and a human-readable message, without creating an issue. Submissions rejected for any other
reason SHALL NOT count toward the limit.

#### Scenario: Fourth submission within a day
- **WHEN** a user who has had 3 submissions accepted in the last 24 hours submits again
- **THEN** the API returns `429` with a message saying the daily submission limit was reached, and no issue is created

#### Scenario: Limit resets after 24 hours
- **WHEN** a user's earliest accepted submission in the window is more than 24 hours old
- **THEN** a new valid submission is accepted

#### Scenario: Failed submission does not count
- **WHEN** a submission fails with `422` or `502`
- **THEN** it does not count toward the user's limit

### Requirement: Create a review issue for each submission
For an accepted submission, the API SHALL open one GitHub issue in the configured LeagueQL repository titled
`[Integration] <name>` and labeled `integration:submitted`, whose body carries every submitted field in the
structured integration format, and SHALL return `201` with the new `issue_number`. User-supplied text SHALL be
rendered so it cannot mention GitHub users or inject Markdown formatting, and the submitter's account identifier
SHALL NOT appear in the issue.

#### Scenario: Successful submission
- **WHEN** a signed-in user submits a valid integration named "Trade Grader"
- **THEN** an issue titled `[Integration] Trade Grader` labeled `integration:submitted` is created and the API
  returns `201` with `{ "issue_number": <n> }`

#### Scenario: Mentions are neutralized
- **WHEN** a submission's description contains `@octocat`
- **THEN** the issue body shows the text literally and GitHub does not notify `octocat`

#### Scenario: No account identifier in the issue
- **WHEN** an issue is created for a submission
- **THEN** the issue title and body contain no Clerk user id

### Requirement: Handle GitHub failures on submission
When GitHub rejects or fails the issue-creation request (non-2xx, timeout, or network error), the API SHALL return
`502` with the message "Couldn't submit right now. Try again in a few minutes.", SHALL raise an operational alert,
and SHALL NOT retry the creation automatically.

#### Scenario: GitHub unavailable
- **WHEN** GitHub returns `500` to the issue-creation request
- **THEN** the API returns `502` with the retry message, an alert is published, and exactly one creation attempt was made

### Requirement: List approved integrations
`GET /integrations` SHALL return, under the standard envelope, every issue in the configured repository labeled
`integration:approved` regardless of open/closed state, each as an item with `issue_number`, `name`,
`category`, `link`, `views`, `description`, `setup_steps`, optional `prompt`, and `featured`
(true when the issue also carries `integration:featured`), ordered newest first. At most one item SHALL be
`featured`: when several approved issues carry `integration:featured`, only the newest SHALL be.

#### Scenario: Only approved issues listed
- **WHEN** the repository has one issue labeled `integration:approved` and one labeled only `integration:submitted`
- **THEN** the response `data.items` contains only the approved one

#### Scenario: Closed approved issue still listed
- **WHEN** an approved issue is closed without removing `integration:approved`
- **THEN** it still appears in `data.items`

#### Scenario: Removing approval delists
- **WHEN** the maintainer removes `integration:approved` from an issue
- **THEN** it no longer appears in `data.items` once the listing cache has expired

#### Scenario: Single featured item
- **WHEN** two approved issues both carry `integration:featured`
- **THEN** only the newer one has `featured: true`

#### Scenario: Maintainer edits are reflected
- **WHEN** the maintainer edits an approved issue's body to fix the description while keeping the structured format
- **THEN** the listed item shows the edited description once the listing cache has expired

### Requirement: Skip malformed approved issues
An approved issue whose body is not in the structured integration format or whose fields fail validation SHALL be
omitted from the listing (and logged), without failing the rest of the listing.

#### Scenario: Broken issue body
- **WHEN** one approved issue's body was edited so it no longer has the integration marker, and two others are valid
- **THEN** `GET /integrations` returns `200` with the two valid items

### Requirement: Cache the listing and tolerate GitHub outages
The API SHALL cache the approved-integration listing for up to 5 minutes, and when GitHub is unreachable SHALL serve
the last successfully fetched listing; only when no listing has ever been fetched SHALL it return `502`.

#### Scenario: Served from cache
- **WHEN** `GET /integrations` is called twice within 5 minutes
- **THEN** GitHub is queried at most once

#### Scenario: GitHub down with a previous listing
- **WHEN** the cache has expired, GitHub returns an error, and a listing was fetched earlier
- **THEN** the API returns `200` with the previously fetched items

#### Scenario: GitHub down with no previous listing
- **WHEN** GitHub returns an error and no listing has ever been fetched
- **THEN** the API returns `502`
