## 1. Shared helper (`src/common/yahoo_tokens.py`)

- [x] 1.1 Add `YahooTokenClient.get_valid_access_token_with_expiry(user)` returning `(token, expires_at)`; make `get_valid_access_token` delegate to it with identical behavior
- [x] 1.2 Add `CachedAccessToken(token_client, user_id)` with lock-guarded `get()` (reuse until `expires_at - TOKEN_EXPIRY_SKEW_SECONDS`) and `invalidate(rejected_token)` (no-op if the cached token differs); never cache failures

## 2. Call sites

- [x] 2.1 `_YahooFetcher` (`src/onboarder/lineup_backfill.py`): resolve via `CachedAccessToken`; on `401` invalidate the used token before the single retry; keep `YahooReauthRequired` → `PermanentBackfillError`
- [x] 2.2 `YahooLeagueClient` (`src/onboarder/yahoo_client.py`): build one `CachedAccessToken` in the constructor instead of `from_env()` per request; invalidate-then-retry in `_fetch_with_auth_retry`; keep the `token_provider` injection point

## 3. Tests

- [x] 3.1 Unit (`tests/unit/common/test_yahoo_tokens.py`): reuse within validity, re-resolve near expiry, invalidate on rejected token, stale-invalidate no-op, failure not cached, concurrent `get()` resolves once
- [x] 3.1a Unit (`tests/unit/common/test_yahoo_tokens.py`): user isolation — build two `CachedAccessToken`s for different users in one process with distinct stored tokens, interleave `get()`/`invalidate()` calls (including a refresh for one user), and assert each only ever returns its own token; also assert the module defines no token cache state at module level
- [x] 3.2 Unit (`tests/unit/onboarder/`): backfill fetcher decrypts once over many requests, 401 retry re-resolves once, revoked link → `PermanentBackfillError`; Yahoo client fan-out decrypts once, concurrent 401s re-resolve once, revoked link → `YAHOO_AUTH`
- [x] 3.2a Unit (`tests/unit/onboarder/`): two `_YahooFetcher`s / `YahooLeagueClient`s for different owners created back-to-back in one process (simulating a warm container) each send only their own owner's token
- [x] 3.3 Component (`tests/component/features/` + `steps/`): add a scenario asserting KMS `Decrypt` call count stays ~constant for a multi-week Yahoo backfill and a Yahoo onboard (mock/spy the KMS client; update the existing Yahoo step defs as needed)
- [x] 3.4 Confirm no frontend change is needed (no new API status or UI state)

## 4. Specs, docs, quality

- [x] 4.1 `openspec validate --all`; archive with `/opsx:archive` once implemented so deltas merge into `yahoo-oauth`, `yahoo-lineup-backfill`, and `league-onboarding`
- [x] 4.2 `uv run ruff check --fix .` and `uv run ruff format .`; run `uv run pytest tests/unit` (keep coverage ~100%, with AWS env stripped per the no-real-boto3 rule) and `uv run behave tests/component`
