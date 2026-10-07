# Tasks

## 1. Frontend

- [x] 1.1 Delete `frontend/src/features/integrations/`.
- [x] 1.2 Remove the `/integrations` route from `frontend/src/app/app.tsx`.
- [x] 1.3 Remove the "Community" group from `app-sidebar.tsx` and delete the integrations nav test.

## 2. Backend

- [x] 2.1 Delete `src/api/integrations.py` and the `/integrations` handlers in `src/api/routes.py`.
- [x] 2.2 Remove the submission-limit helpers from `src/api/helpers.py`.
- [x] 2.3 Delete the integrations unit + component tests and `TestIntegrationSubmissionLimit`.

## 3. Infrastructure

- [x] 3.1 Remove the GitHub env vars (`regional/main.tf`), the `POST /integrations` throttle (`modules/api-gw`), and the GitHub-token IAM statement (`global/{dev,prod}`).

## 4. Docs & quality

- [x] 4.1 Update `docs/api/openapi_spec.yaml`, `docs/db/dynamodb_spec.md`, and the architecture diagram (+ PNG).
- [x] 4.2 Run ruff, `npm run format:fix`, `npm run lint`, `npm run build:ci`, pytest, behave, vitest, and `openspec validate --all`.
