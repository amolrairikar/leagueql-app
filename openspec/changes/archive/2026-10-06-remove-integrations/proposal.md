# Proposal

## Why

The community Integrations page (GitHub-issue-backed submissions and an approved-integrations showcase) is being
retired. Removing it drops the GitHub PAT dependency, two API endpoints, a DynamoDB item type, and a frontend page.

## What Changes

- **BREAKING**: `GET /integrations` and `POST /integrations` are removed.
- The sidebar "Community" group (whose only item was "Integrations") and the `/integrations` route are removed.
- The per-user `USER#<sub>` / `INTEGRATION_SUBMISSIONS` DynamoDB item is no longer read or written (existing items
  expire via their 24h TTL).
- Infra: the Lambda's `GITHUB_TOKEN_SSM_PARAM` / `GITHUB_REPO` env vars, the GitHub-token SSM IAM statement, and the
  `POST /integrations` API Gateway throttle are removed.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `backend/integrations`: all requirements removed (capability retired).
- `frontend/integrations`: all requirements removed (capability retired).

## Impact

- **Backend**: delete `src/api/integrations.py`; drop the handlers in `src/api/routes.py` and the submission-limit
  helpers in `src/api/helpers.py`; delete their unit + component tests.
- **Frontend**: delete `frontend/src/features/integrations/`; drop the route in `app.tsx` and the Community group in
  `app-sidebar.tsx`; delete the nav test.
- **Infra**: `infrastructure/regional/main.tf`, `infrastructure/modules/api-gw/main.tf`,
  `infrastructure/global/{dev,prod}/main.tf`.
- **Docs**: OpenAPI spec, DynamoDB spec, architecture diagram (GitHub Issues node removed).
- **Manual cleanup** (outside this change): delete the `/leagueql/<env>/github/token` SSM parameter, revoke the PAT,
  and optionally close the `integration:*` issues and delete the labels.
