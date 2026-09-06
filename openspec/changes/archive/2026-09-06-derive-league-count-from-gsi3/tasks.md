## 1. sync-counts worker: derive count from GSI3

- [x] 1.1 In `workers/sync-counts/index.js`, replace the `GetItemCommand` import/usage with a `QueryCommand` against `IndexName="GSI3"`, `KeyConditionExpression="SK = :sk"`, `:sk={S:"METADATA"}`, `Select="COUNT"`, looping on `ExclusiveStartKey`/`LastEvaluatedKey` and summing `res.Count`; keep the credential guard, the `COUNTS_KV.put("leagueCount", String(count))` write, and the log line. (Code done; live `npx wrangler dev --test-scheduled` verification is a deploy-time step — needs prod AWS creds.)
- [x] 1.2 Wrap the GSI3 query + `COUNTS_KV.put` + success log in a `try`/`catch` in `workers/sync-counts/index.js`; the `catch` logs the failure reason (with stack) via `console.error` and leaves the previously-synced KV value untouched (no clobber to 0). See design.md — Decisions.
- [ ] 1.3 Update the IAM policy on the worker's access-key user: replace `dynamodb:GetItem` on the table ARN (scoped by the `APP#STATS` `LeadingKeys` condition) with `dynamodb:Query` on the `arn:aws:dynamodb:*:<account>:table/leagueql-table-prod/index/GSI3` index ARN, and drop the `LeadingKeys` condition (it targets the base-table PK, which a GSI query does not constrain). This user is created manually (not in Terraform), so apply it in the AWS console. (Deferred: requires AWS console access.)
- [ ] 1.4 Confirm the derived value matches `aws dynamodb query --table-name leagueql-table-prod --index-name GSI3 --key-condition-expression "SK = :sk" --expression-attribute-values '{":sk":{"S":"METADATA"}}' --select COUNT`, and that the deployed worker logs `Synced league count: N` (not an error) after the policy update. (Deferred: requires live AWS access at deploy time.)

## 2. Remove the maintained-counter backend writes

- [x] 2.1 Delete `update_league_count` and its onboard call site (the `if previous_version_id is None:` increment) in `src/processor/handler.py`; verified `grep` returns nothing.
- [x] 2.2 Delete `update_league_count` from `src/api/helpers.py`, its `delta=-1` call and import in `src/api/routes.py`, and its re-export in `src/api/main.py`. Also removed the additional consumer `scripts/utility_scripts/delete_league.py` (import + `delta=-1` call). Verified `grep -rn update_league_count src/ scripts/` returns nothing.
- [x] 2.3 Removed the `ADD league_count -1` update, the `decrement_league_count` function, the `--fix-league-count` CLI flag, and the docstring reference in `scripts/utility_scripts/find_orphaned_leagues.py`; verified `grep` returns nothing.

## 3. Docs

- [x] 3.1 In `docs/db/dynamodb_spec.md`, removed the `APP#STATS`/`LEAGUE_COUNT` item description and added a note that the count is derived from the GSI3 `SK="METADATA"` query; verified no `LEAGUE_COUNT` reference remains.

## 4. Tests

- [x] 4.1 Updated backend unit tests to drop counter expectations: `tests/unit/processor/test_pure_functions.py` (removed `TestUpdateLeagueCount`), `tests/unit/processor/test_handler.py` (removed the `update_league_count` patch kwargs + increment/not-called assertions), `tests/unit/api/test_utils.py` (removed `TestUpdateLeagueCount`), `tests/unit/api/test_endpoints.py` (removed the decrement-on-delete test). `pipenv run pytest` on the affected files passes (380 passed).
- [x] 4.2 Updated backend component steps: removed the `LEAGUE_COUNT` seed step from `tests/component/steps/api_steps.py` and the counter-value `@then` from `tests/component/steps/onboarding_steps.py`; dropped the counter lines/wording from `api_delete_league.feature`, `league_refresh.feature`, and `onboard_to_processed.feature`. `pipenv run behave tests/component` passes (56 scenarios).

## 5. Verification & hygiene

- [x] 5.1 `grep -rn "LEAGUE_COUNT\|update_league_count\|league_count" src/ scripts/ tests/ docs/ workers/` returns no runtime references.
- [x] 5.2 Ran `pipenv run ruff check --fix . && pipenv run ruff format .` (all checks passed); `openspec validate --all` passes.
