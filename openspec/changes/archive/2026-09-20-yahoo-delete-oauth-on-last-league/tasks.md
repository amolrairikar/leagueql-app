# Tasks

## 1. Token engine
- [x] 1.1 Add `YahooTokenClient.delete_tokens(clerk_user_id)` deleting the `USER#{id}/YAHOO_OAUTH` item (idempotent).
- [x] 1.2 Add a `delete_tokens` module wrapper in `src/api/yahoo_oauth.py`.

## 2. Ownership check
- [x] 2.1 Add `owner_has_other_yahoo_leagues(clerk_user_id, exclude_canonical_league_id)` in `src/api/helpers.py` querying GSI3.

## 3. Delete route
- [x] 3.1 In `delete_league`, after the DB + S3 delete, when the deleted league's effective platform is Yahoo and the owner has no other Yahoo leagues, delete their token item (best-effort).
- [x] 3.2 Guard the whole cleanup (ownership check + delete) so any failure — including the GSI3 query — is alerted and never fails the already-completed delete.

## 3a. Infrastructure
- [x] 3a.1 Grant the API role `dynamodb:Query` on `/index/GSI3` (primary + replica) in prod and dev `main.tf`.

## 4. Tests
- [x] 4.1 Unit tests: `delete_tokens` (engine + wrapper), `owner_has_other_yahoo_leagues`.
- [x] 4.2 Component tests: delete last Yahoo league removes token; delete with another Yahoo league keeps it; delete ESPN/Sleeper leaves any token untouched.
- [x] 4.3 Regression unit test: a ClientError from the ownership-check query still returns 200 (alerted, no token removed).

## 5. Verify
- [x] 5.1 `openspec validate --all` passes.
- [x] 5.2 Ruff lint + format; unit + component tests pass.
