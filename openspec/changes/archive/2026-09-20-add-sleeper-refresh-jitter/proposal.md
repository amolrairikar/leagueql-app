## Why

The scheduled Sleeper auto-refresh Lambda dispatches an async onboarder invocation for every onboarded Sleeper league in a tight, back-to-back loop, so every onboarder (and its burst of Sleeper API calls) starts at essentially the same instant — hammering the Sleeper API simultaneously each week. There is no time urgency to this refresh, so the load can be spread out.

## What Changes

- Spread the per-league onboarder invocations across a randomized time window ("jitter") instead of dispatching them all at once, so the Sleeper API is hit gradually over the window rather than in one simultaneous burst.
- The spread window is configurable via a new `REFRESH_JITTER_WINDOW_SECONDS` environment variable (default ~10 minutes); `0` disables jitter (preserving today's immediate-dispatch behavior). A single-league run also dispatches immediately.
- All other refresh behavior is unchanged: which leagues are selected, the per-league correlation-id trace, and the raise-after-loop-on-any-failure semantics that let EventBridge retry the whole (idempotent) run.
- Infra: raise the `leagueql-sleeper-refresh` Lambda timeout so it can outlast the spread window, and set the new env var. No new components.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `backend/scheduled-sleeper-auto-refresh`: adds a requirement that per-league dispatches are spread across a randomized, bounded, configurable jitter window (rather than an immediate loop), and clarifies the existing in-season dispatch scenario to reflect staggered invocations.

## Impact

- Code: `src/sleeper_refresh/handler.py` (jitter logic in the dispatch loop).
- Infra: `infrastructure/regional/main.tf` — `module "sleeper_refresh_lambda"` timeout bump (60s → 900s) and new `REFRESH_JITTER_WINDOW_SECONDS` env var.
- Tests: `tests/unit/sleeper_refresh/test_handler.py` (jitter branches, with `time.sleep` patched) and `tests/component/features/sleeper_auto_refresh.feature` (run with window `0` for determinism).
- No API contract, DynamoDB schema, or architecture-diagram change (no new/removed/rewired component); the onboarder invoke contract and the shared onboarder Lambda are untouched, so user-facing onboarding is unaffected.
