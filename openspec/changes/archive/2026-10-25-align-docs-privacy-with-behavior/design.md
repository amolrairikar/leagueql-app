# Design

## Context

The public docs had drifted from the backend in a few places where the backend design is
account-level rather than league-level:

- ESPN cookies live in a single `USER#{id}/ESPN_CREDENTIALS` item. `DELETE /leagues/{id}` and
  `PUT /leagues/{id}/auto-refresh` remove it only when `owner_has_other_optedin_espn_leagues` is
  false (`src/api/routes.py`).
- Yahoo OAuth tokens are per user. League delete removes them only when
  `owner_has_other_yahoo_leagues` is false.
- `_refresh_block_reason` enforces a 7-calendar-day cooldown (429), an offseason block (409), and an
  already-current block (409).
- `frontend/src/lib/telemetry.ts` stamps `user.id` on every browser span and exports to Better Stack
  through the same-origin `/ingest/traces` proxy.

## Decisions

- **Describe behavior, not implementation.** The copy says "one set of stored cookies is shared by
  all of your ESPN leagues" rather than naming DynamoDB items, matching the existing rule of not
  exposing encryption or storage internals.
- **Diagnostics disclosed plainly.** We say diagnostics are tagged with the account ID instead of
  calling them anonymous, because `user.id` really is attached.
- **Deletion = what exists today.** No self-serve account or membership deletion exists, so the
  policy points those requests to support@leagueql.com instead of promising a feature.
- **Refresh limits stated without exact error text** so the copy survives wording tweaks to the
  429/409 messages.

## Risks / Trade-offs

- The copy now encodes the cooldown length (one week). If `REFRESH_COOLDOWN_DAYS` changes, the
  User Guide and FAQ must change with it; the spec scenarios call this out so the drift is caught.
