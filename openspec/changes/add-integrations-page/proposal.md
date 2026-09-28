# Proposal

## Why

League managers already use the export ZIP (per-season view JSON, `README.md`, `manifest.json`) to build their own
tools — AI prompts, spreadsheets, bots, dashboards — but there is nowhere to discover or share them. An
Integrations page lets people browse what others have built and submit their own, with the maintainer reviewing
every submission before it is listed.

## What Changes

- New **Integrations** page (`/integrations`) inside the signed-in app shell, reached from a new "Community"
  sidebar group: a "How it works" strip, a featured integration, category filter chips, search, a card grid, and a
  detail dialog (setup steps, views read, optional copyable prompt, external link).
- New **"Submit your integration"** dialog that sends the submission to the backend.
- New authenticated endpoint `POST /integrations`: validates the submission, enforces a per-user limit of 3
  submissions per rolling 24 hours, and opens a GitHub issue in the LeagueQL repository labeled
  `integration:submitted` for maintainer review.
- New authenticated endpoint `GET /integrations`: lists issues the maintainer has labeled `integration:approved`
  (open or closed), parsed from the structured issue body; `integration:featured` marks the featured one.
- New `integrations` feature flag gating everything above: when off, both endpoints return 404 and the nav item and
  route are hidden. It is exposed through the existing whitelist in `GET /feature-flags` (no change to the flag
  layer's requirements).
- New dependency on the GitHub REST API via a repo-scoped fine-grained token stored in SSM.

## Capabilities

### New Capabilities
- `backend/integrations`: submitting integrations as GitHub issues, listing approved integrations, validation,
  per-user submission limit, GitHub-failure handling, and feature-flag gating of both endpoints.
- `frontend/integrations`: the Integrations page, filtering/search, featured card, detail dialog, submit dialog
  (success / limit / failure states), and flag-gated nav item and route.

### Modified Capabilities
<!-- None: backend/feature-flags and frontend/feature-flags already require new flags to be exposed via the
     explicit whitelist; adding `integrations` to it changes no requirement. -->

## Impact

- **Backend:** `src/api/routes.py`, `src/api/main.py` (request model), new `src/api/integrations.py` (GitHub
  client + issue body format), `src/common/feature_flags.py`, `src/api/helpers.py` (submission limit).
- **API contract:** two new operations in `docs/api/openapi_spec.yaml`; `integrations` added to the
  `FeatureFlagsResponse` schema.
- **Data model:** new per-user submission-counter item in `docs/db/dynamodb_spec.md`.
- **Infrastructure:** API Lambda env vars (`GITHUB_TOKEN_SSM_PARAM`, `GITHUB_REPO`), IAM read on the token
  parameter (dev + prod), API Gateway throttling for `POST /integrations`; architecture diagram gains GitHub as an
  external dependency.
- **Manual setup:** fine-grained PAT at `/leagueql/<env>/github/token`, repo labels `integration:submitted`,
  `integration:approved`, `integration:featured`, and `"integrations"` added to the SSM feature-flag JSON.
- **Frontend:** new `frontend/src/features/integrations/`, `src/lib/feature-flags.ts`, `src/app/app.tsx`,
  `src/features/sidebar/app-sidebar.tsx`.
