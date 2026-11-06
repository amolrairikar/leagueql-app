# Design

## Context

`YahooTokenClient.get_valid_access_token(user)` (`src/common/yahoo_tokens.py`) reads the
`USER#/YAHOO_OAUTH` item and KMS-decrypts the access token on every call, refreshing only when within
`TOKEN_EXPIRY_SKEW_SECONDS` of `expires_at`. Two onboarder paths call it per HTTP request:

- `_YahooFetcher._send` (`src/onboarder/lineup_backfill.py`): one call per roster GET, ~1/s,
  thousands per season across leagues.
- `YahooLeagueClient._auth_headers` (`src/onboarder/yahoo_client.py`): one call per URL in
  `fetch_all()`, and it builds a fresh `from_env()` client (new boto3 KMS client) each time.

Prod CloudTrail: ~4.3k of ~5k sampled `Decrypt` calls from the backfill role, ~450 from the onboarder.
Access tokens last one hour, so one decrypt per run is enough.

## Goals / Non-Goals

**Goals:** ~1–2 decrypts per run instead of one per request; unchanged error semantics
(`YahooReauthRequired`, `PermanentBackfillError`); no duplicate resolution under concurrency; token
never persisted or logged beyond process memory.

**Non-Goals:** the Yahoo player-stats refresher (one decrypt per page, weekly — negligible); ESPN
cookie decrypts; envelope encryption / data-key caching; cross-invocation caching (Lambda warm
containers, S3, DynamoDB); changing the stored schema.

## Decisions

1. **A small `CachedAccessToken` helper in `src/common/yahoo_tokens.py`**, not a cache inside
   `YahooTokenClient`. It wraps `(token_client, user_id)` and exposes `get()` and
   `invalidate(rejected)`. Rationale: `from_env()` builds a new client per call at the Yahoo client
   call site, so a client-level cache would not survive; and scoping the cache to one run/object
   guarantees it can never serve user A's token to user B or outlive the run. Alternative (module
   global dict keyed by user) rejected: warm Lambda containers would hold decrypted tokens across
   invocations and complicate tests/revocation.
2. **Expiry handling.** The helper needs `expires_at`, which `get_valid_access_token` doesn't return.
   Add a sibling `YahooTokenClient.get_valid_access_token_with_expiry(user) -> (token, expires_at)`
   (refactor: `get_valid_access_token` delegates to it, behavior unchanged). `get()` returns the
   cached token while `expires_at - TOKEN_EXPIRY_SKEW_SECONDS > time.time()`, else re-resolves. After
   a refresh, `expires_at` is `now + expires_in` from the token response.
3. **Concurrency.** `get()` and `invalidate()` hold a `threading.Lock` across the resolve. The
   onboarder's coroutines call the sync resolver inline, so the lock is cheap and protects any
   executor-thread use. `invalidate(rejected_token)` is a no-op unless the cached token still equals
   `rejected_token`, so N in-flight requests that all 401 on the same stale token cause one
   re-resolution, not N.
4. **401 handling.** `_YahooFetcher.get` and `YahooLeagueClient._fetch_with_auth_retry` call
   `invalidate(token_used)` before the single retry, then `get()` re-reads the stored item (picking
   up a token another process refreshed). A second `401` behaves as today (permanent error /
   failure). Note the existing code's "retry gets a fresh one" comment was only true near expiry;
   this makes the retry re-read explicitly.
5. **User isolation.** Each `CachedAccessToken` is bound to exactly one `user_id` at construction and
   is owned by the single-run object that uses it (`_YahooFetcher`, `YahooLeagueClient`). There is
   **no module-level or class-level token state** and no user-keyed lookup, so one user's token can
   never be returned for another user, and nothing survives a run in a warm Lambda container. A unit
   test pins this (two users interleaved in one process); future "optimizations" must not move the
   cache to shared state. The owner id still comes from the same event/metadata source as today.
6. **Error mapping unchanged.** `YahooReauthRequired` propagates out of `get()` uncached (failures
   are never cached); the backfill still wraps it in `PermanentBackfillError`, the onboarder still
   maps it to `YAHOO_AUTH`.
7. **Client reuse.** Each Yahoo client/fetcher builds its token client once in its constructor
   (the fetcher already does; `YahooLeagueClient` stops calling `from_env()` per request), but the
   `token_provider` injection point is kept so existing tests still inject a plain callable.

## Risks / Trade-offs

- A token revoked/rotated mid-run stays in use until Yahoo `401`s it or it nears expiry (≤ ~1 h
  cached). Mitigated by the 401 invalidate-and-retry; the behavior matches what a per-request read
  would do against Yahoo's own validation anyway.
- Decrypted token lives in process memory for the run. It was already in memory per request; no new
  exposure surface, and it is never logged (existing no-token-in-logs scenarios still apply).
- Thread-safety bugs would show as duplicate decrypts, not wrong tokens; covered by a concurrency test.

## Migration / Rollout

No data or infra changes; deploy via the normal Lambda pipeline. Verify afterwards with CloudTrail:
prod `Decrypt` count per backfill/onboard run should drop from thousands to a handful.

## Open Questions

None blocking. Optional follow-up: share one decrypted ESPN cookie pair per owner across a scheduled
refresh, if ESPN decrypt volume ever matters.
