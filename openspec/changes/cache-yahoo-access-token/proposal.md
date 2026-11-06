# Proposal

## Why

The Yahoo lineup backfill and the onboarder's Yahoo client call `get_valid_access_token()` before
every Yahoo HTTP request, and each call does a DynamoDB read plus a KMS `Decrypt`. CloudTrail showed
~19k prod `Decrypt` calls in 5 days (AWS KMS free tier is 20k/month), ~85% from
`leagueql-prod-lineup-backfill-role` and most of the rest from the onboarder role. The access token
lives for an hour, so decrypting it once per run is enough.

## What Changes

- The lineup backfill's Yahoo fetcher resolves the owner's access token once and reuses the
  decrypted value until it is within the expiry skew of `expires_at`, instead of once per request.
- The onboarder's Yahoo league client does the same across its per-league fan-out (settings,
  standings, teams, draft, transactions, game weeks, one scoreboard per week).
- A `401` drops the cached token so the retry re-reads the stored item (picking up a token another
  process refreshed) rather than reusing the rejected one.
- Concurrent callers sharing one cached token never trigger duplicate decrypts/refreshes.
- Revoked or missing links still surface exactly as today (`YahooReauthRequired`, and
  `PermanentBackfillError` in the backfill).
- No change to what is stored, to tokens in logs/traces, to pacing, or to API/DynamoDB schemas.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `backend/yahoo-oauth`: the transparent-refresh requirement gains the rule that a run reuses one
  decrypted access token until its expiry skew, and re-resolves it after a `401`.
- `backend/yahoo-lineup-backfill`: a season backfill resolves the owner's Yahoo token once, not per
  roster request.
- `backend/league-onboarding`: the onboarder's Yahoo token requirement gains the same
  once-per-run reuse across its concurrent fetches.

## Impact

- Code: `src/common/yahoo_tokens.py` (new small cached-token helper), `src/onboarder/lineup_backfill.py`
  (`_YahooFetcher`), `src/onboarder/yahoo_client.py` (`_auth_headers` / `_fetch_with_auth_retry`).
  The Yahoo player-stats refresher is out of scope (one decrypt per page, weekly).
- Tests: backend unit tests for the helper and both call sites; Behave component scenarios for the
  backfill and Yahoo onboarding chain. No frontend change.
- Docs: no OpenAPI, DynamoDB, or architecture diagram change (no new component).
- Cost/ops: cuts prod KMS `Decrypt` volume from thousands per run to ~1–2.
