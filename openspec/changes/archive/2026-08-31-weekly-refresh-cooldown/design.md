## Context

See proposal.md — Why. A per-league refresh cooldown already exists: `POST /leagues?requestType=REFRESH`
reads `last_refresh_at` off the METADATA item and rejects with `429` when it is within
`REFRESH_COOLDOWN_MINUTES = 30`. `last_refresh_at` is written by the processor at the end of a
successful refresh (`write_metadata_items`). The frontend submit loop treats `429`/`409` as
non-retryable and then nulls the failure reason, so the backend message never reaches the user.

## Goals / Non-Goals

**Goals:**
- Cap manual refreshes at once per rolling 7-day window.
- Give the user a clear, benign message about when they can refresh again.

**Non-Goals:**
- Changing the DynamoDB schema (reuses `last_refresh_at`).
- Adding a proactive "next refresh available on <date>" display before the user clicks (no new
  `getLeague` field — the message rides on the existing submit response).
- Making the window configurable per-deployment (stays a module constant, matching the current pattern).
- Changing the scheduled Sleeper auto-refresh path.

## Decisions

- **Rolling 7-day window, not calendar week.** Reuses the existing elapsed-time check almost
  verbatim — swap `timedelta(minutes=REFRESH_COOLDOWN_MINUTES)` for `timedelta(days=REFRESH_COOLDOWN_DAYS=7)`.
  Predictable and minimal. Calendar-week reset was considered but needs week-boundary logic for no
  real user benefit.
- **Human-readable remaining-wait message via a small helper.** A 7-day window makes the old
  "wait 10080 minutes" phrasing absurd. A module-level `_format_cooldown_wait(remaining)` helper
  formats the remaining `timedelta` as days (and sub-day hours), kept separate so it is unit-testable.
- **Surface the benign response on the frontend by reusing the `NOT_STARTED` pattern.** The submit
  loop already has a special-case (`failureCode` sentinel) that renders a message without the
  contact-support prompt. Capture the caught `ApiError` for `429`/`409`, set `failureReason` to its
  `message` and a `COOLDOWN` sentinel code, and render a neutral title. No new component or API field.
- **Also surface `409` (already-up-to-date / in-progress), not just `429`.** Same discarded-message
  code path; both are benign and improve the UX for the same trivial cost.

## Risks / Trade-offs

- [The scheduled Sleeper auto-refresh writes `last_refresh_at`, so it can block a manual Sleeper
  refresh for up to 7 days] → Acceptable: the "already up to date" `409` short-circuit already
  covers the common case where the scheduled job kept the data current, and Sleeper users get
  automatic freshness anyway. No exemption logic; ESPN (no scheduled path) is the primary consumer
  of the manual weekly cap.
- [A legitimate need to refresh sooner — e.g. a correction — is now blocked for a week] → The
  benign message tells the user exactly when they can retry; a much longer wait than before is the
  intended trade-off for reduced pipeline load.
