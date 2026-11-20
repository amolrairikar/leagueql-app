# Tasks

## 1. Access log format

- [x] 1.1 Add `userId = "$context.authorizer.claims.sub"` to `access_log_settings.format` in `infrastructure/modules/api-gw/main.tf`, leaving all existing keys unchanged; verify with `terraform fmt -check` and `terraform validate` in `infrastructure/regional`
- [ ] 1.2 Run `terraform plan` for dev and verify the only change is the `$default` stage's `access_log_settings.format` (no other resources replaced)

## 2. Docs and specs

- [x] 2.1 Check `frontend/src/features/privacy/privacy-page.tsx` for any enumeration of logged data; update it if it lists what request logs contain, otherwise note none needed (verify by reading the page text)
- [x] 2.2 Run `npx @fission-ai/openspec@latest validate --all` and verify the new `backend/api-access-logging` delta passes

## 3. Rollout verification

- [ ] 3.1 After dev apply, make an authenticated API call and verify the newest entry in `/aws/apigateway/leagueql-api-dev-east` has a non-empty `userId` matching the caller's Clerk ID
- [ ] 3.2 After prod apply, verify an authenticated request logs `userId` and a public route (`GET /health`) logs an empty/placeholder `userId` with a normal response

## Workflow follow-up

- Archive with `/opsx:archive` once deployed and verified, so `backend/api-access-logging` is added to `openspec/specs/`.
- No application code, backend/frontend tests, OpenAPI, DynamoDB spec, or architecture diagram changes are required (no component deployed, removed, or rewired).
