## Context

See proposal.md - Why. The 7-day cooldown is enforced in one place: the refresh branch of
the onboard endpoint in `src/api/routes.py` (~line 277-287), which raises `429` when
`now - last_refresh_at < timedelta(days=REFRESH_COOLDOWN_DAYS)`. The `ENVIRONMENT` env var
(`"dev"` / `"prod"`) is already injected into the API Lambda by Terraform
(`infrastructure/regional/main.tf`) and read at runtime elsewhere (`src/common/tracing.py`).

## Goals / Non-Goals

- Goal: DEV refreshes are never blocked by the weekly cooldown.
- Non-Goal: changing PROD behavior, the concurrency guard, or the "already up to date" guard.
- Non-Goal: a runtime-toggleable flag or any infra change.

## Decisions

- **Gate on `ENVIRONMENT == "dev"`, read at request time.** Skip the cooldown block when the
  env var is `"dev"`. Reading `os.environ.get("ENVIRONMENT")` inside the handler (rather than a
  module-level constant) keeps it trivially monkeypatchable in unit tests and avoids import-order
  coupling. `os` is already imported in `routes.py`.
  - _Alternative — feature flag via `common/feature_flags`:_ more flexible (runtime toggle per
    env) but heavier for a dev-convenience change with no need for per-request toggling. Rejected.
  - _Alternative — make `REFRESH_COOLDOWN_DAYS` conditional in `main.py`:_ conflates the constant's
    meaning with an environment concern and is harder to read than a guard at the enforcement site.
    Rejected.

## Risks / Trade-offs

- [DEV data churn from unlimited refreshes] → acceptable; DEV is a testing environment and the
  concurrency guard still prevents overlapping refreshes.
- [Misconfigured `ENVIRONMENT` in PROD could disable the cooldown] → PROD sets `ENVIRONMENT=prod`
  via Terraform; the check is `!= "dev"`, so any unset/other value keeps the cooldown on.
