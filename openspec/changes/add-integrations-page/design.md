# Design

## Context

See proposal.md for motivation and specs/ for requirements. Relevant current state:

- The API is one FastAPI app on Lambda behind API Gateway HTTP API. Routes are declared individually in
  `docs/api/openapi_spec.yaml` (API Gateway only routes what the spec lists), protected by the Clerk JWT authorizer;
  handlers read the user via `get_authenticated_user` in `src/api/routes.py`.
- Feature flags: `src/common/feature_flags.py` (`is_enabled`), whitelisted in `get_feature_flags`; frontend reads them
  synchronously via `isEnabled` in `frontend/src/lib/feature-flags.ts`, and the tree remounts on change.
- Secrets live in manually created SSM SecureString parameters, read once per cold start via
  `get_secret_from_env_param` (`src/common/secrets.py`), as `src/discord_notifier/handler.py` does.
- Outbound HTTP uses `requests`; `build_retry_session()` (`src/common/http.py`) retries GETs only.
- The export's view names are the keys of `EXPORT_SEASON_VIEWS` in `src/api/main.py` plus `teams`.
- The app runs in two regions, each with its own API Lambda and containers.
- Frontend loads data with `toResult` + `<Suspense>` + `use()`, mutates with local state + `<ErrorAlert>`, and has no
  toast, textarea, or checkbox component (native checkboxes are the convention).

## Goals / Non-Goals

**Goals:**
- GitHub is the only store and review tool for integrations: no new table for listings, no admin UI.
- The page keeps working (from cache) through short GitHub outages.

**Non-Goals:**
- Usage counts ("used by N leagues"), per-platform tags, screenshots/uploads, editing or withdrawing a submission
  from the app, notifying the submitter when approved.
- Pagination beyond 100 approved integrations.

## Decisions

### GitHub access: fine-grained PAT in SSM
A fine-grained token scoped to `amolrairikar/leagueql-app` with Issues read/write, at
`/leagueql/<env>/github/token`, exposed to the API Lambda as `GITHUB_TOKEN_SSM_PARAM`; repo from `GITHUB_REPO`.
Read once per cold start. *Alternative:* a GitHub App — decoupled from a personal account, but needs a private key,
JWT→installation-token exchange, and more setup for a single-repo, low-volume use. Can migrate later behind the same
module.

### Issue body format: issue-form-style sections with a version marker
`build_issue_body` writes `<!-- leagueql-integration:v1 -->` then `### Name`, `### Author`, `### Category`,
`### Link`, `### Views`, `### Description`, `### Setup steps`, optional `### Prompt`. `parse_issue_body` splits on
`### ` headings, requires the marker, and re-validates every field with the same rules as the request model
(shared Pydantic model), returning `None` on any failure. This is human-readable in GitHub, lets the maintainer fix
typos before approving, and the marker lets a future `v2` coexist. *Alternative:* a hidden JSON blob — trivially
parseable but maintainer edits to the visible text would silently not apply.

Neutralizing user text: single-line values go in inline code spans (with backticks stripped), multi-line values
(description, steps, prompt) in fenced code blocks using a fence longer than any backtick run in the content. Code
spans/blocks suppress @mentions, autolinks, and Markdown. The parser strips these wrappers.

### Labels as the review workflow
`integration:submitted` on creation; the maintainer adds `integration:approved` to list and `integration:featured` to
feature. Listing uses `GET /repos/{repo}/issues?labels=integration:approved&state=all&per_page=100&sort=created&direction=desc`
(labels filter is AND; PRs are excluded by skipping items with `pull_request`). Newest `integration:featured` wins.
*Alternative:* Projects v2 status field — needs GraphQL and project scopes.

### Listing cache: in-memory, 5-minute TTL, stale-on-error
Module-level `(items, fetched_at)` like `feature_flags.py`. On expiry, refetch; on GitHub error, return the stale
items if any, else raise → `502`. Per-container and per-region caches mean approval can take up to ~5 minutes to show
everywhere, which is acceptable. At 5000 req/h for an authenticated PAT, even many cold containers stay well under
the limit. *Alternative:* DynamoDB cache item or a GitHub webhook → DynamoDB sync — consistent across containers but
adds a table item, a webhook endpoint and secret; unnecessary at this volume.

### Issue creation: single attempt, no retry
A plain `requests.post` (not the retry session) with `timeout=(5, 10)`. A retry after a timeout could create a
duplicate issue; the user can resubmit instead. Failures publish an alert via the existing `publish_failure` path.

### Submission limit: DynamoDB timestamp list per user
Item `PK=USER#<sub>`, `SK=INTEGRATION_SUBMISSIONS`, attribute `submitted_at` (list of epoch seconds) and `ttl` =
latest + 24h. Before creating the issue: read, drop entries older than 24h, reject with `429` if 3 remain. After a
successful create: write the pruned list plus now. Only successful creates are recorded, satisfying "failed
submissions don't count". The read-check-write race is acceptable: API Gateway throttles `POST /integrations` to
burst 1 / rate 1, and the worst case is one extra issue. *Alternative:* conditional update with a counter — atomic,
but a fixed-window counter can't express a rolling 24h window or skip failed attempts cleanly.

### Endpoints live in `routes.py`; GitHub/format logic in `src/api/integrations.py`
Matches the single-router convention; the new module holds the GitHub client, body format, and cache so it can be
unit-tested without FastAPI. Tests patch `integrations.requests` / the session.

### Frontend structure
`frontend/src/features/integrations/` with `integrations-page.tsx`, `integration-card.tsx` (category preview
illustrations from the mockup), `integration-detail-dialog.tsx`, `submit-integration-dialog.tsx`, `api-calls.ts`,
`types.ts`, `constants.ts`. Route added to `APP_LAYOUT_ROUTES` only when `isIntegrationsEnabled()`, else a
`<Navigate to="/home">`; sidebar gets a "Community" `SidebarGroup`. Textareas are native `<textarea>` styled like
`Input`; "Copied" button state replaces a toast. External links use `target="_blank" rel="noopener noreferrer"`, and
all listed text renders as React text (never HTML).

## Risks / Trade-offs

- [PAT tied to a personal account and expires] → Set a long expiry, calendar a rotation reminder; `502` + Discord
  alert on auth failure makes an expired token obvious.
- [Spam fills the repo with issues] → Signed-in only, 3/user/24h, API Gateway throttle; maintainer can close/lock.
  Revisit (captcha, GitHub App with separate repo) if it becomes a problem.
- [Public repo exposes submissions before review] → Submissions are meant to be public anyway; no account identifiers
  are written; form copy tells users not to include league data or credentials.
- [Maintainer edit breaks the format] → Malformed issues are skipped and logged instead of failing the page.
- [Up to ~5 min / per-region delay after approval] → Documented; acceptable for a curated list.
- [Malicious link on an approved card] → Only `https` accepted, maintainer reviews every link before approval, links
  open with `noopener noreferrer`.

## Migration Plan

1. Manual: create the PAT, `/leagueql/<env>/github/token` SecureString, the three repo labels, and add
   `"integrations": {"enabled": false}` to each env's feature-flag parameter.
2. Deploy infrastructure + backend (env vars, IAM, throttling, OpenAPI routes, endpoints).
3. Deploy the frontend (hidden while the flag is off).
4. Enable the flag in dev, verify end to end, then prod.

Rollback: turn the flag off (hides the page, endpoints return 404); no data migration to undo.
