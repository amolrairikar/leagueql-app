# Design

## Context

See proposal.md — Why. Failed per-request fetches are already isolated into
`{"data": None}` by `fetch_one` (`src/onboarder/utils.py`); the all-or-nothing behavior
comes from `validate_api_results`, which raises `RuntimeError` on the **first** `None`.
That error propagates out of `OnboardingService.run()` and the handler records it as an
`UPSTREAM` `502`. All three clients (ESPN, Sleeper, Yahoo) funnel their gathered results
through `validate_api_results`, so it is the single choke point for this behavior.

Each result dict already carries its `season`, which makes per-season grouping possible
without any new plumbing through the fetch layer.

## Goals / Non-Goals

**Goals:**
- Onboard seasons whose API calls all succeed; skip seasons with any failed call; fail
  the whole onboard only when every season fails.
- Keep the change in the shared validation path so all platforms benefit uniformly.
- Keep the persisted `seasons` set and the S3 manifest consistent with only the seasons
  actually onboarded.

**Non-Goals:**
- Surfacing which seasons were skipped to the user (silent partial onboard).
- Changing how an all-seasons failure is classified/paged — it stays `UPSTREAM`/`502`
  (a per-season async `401` still loses its HTTP status en route to `data: None`).
- Any API-contract, DynamoDB-schema, architecture-diagram, or frontend change.

## Decisions

- **Group by season inside `validate_api_results`.** Return only results for seasons with
  zero `None`s; raise `RuntimeError` only when no season survives (preserving the
  all-fail → `UPSTREAM`/`502` path and empty-input → `[]`). A gathered non-`Exception`
  `BaseException` (e.g. cancellation) is un-attributable to a season, so it keeps raising
  as today. Alternative — a new sibling function and leaving the old one for some callers
  — was rejected: one shared choke point is simpler and gives uniform cross-platform
  behavior, which the user chose.
- **Validate Sleeper once over the combined results.** Sleeper fetches draft picks in a
  second round and currently validates each round separately; per-season dropping applied
  per round could keep a season's main data while dropping its picks. Restructure
  `SleeperClient.fetch_all` to build pick URLs from the **raw** main results
  (`_build_draft_pick_urls` already skips `None` `drafts` via its `isinstance(list)`
  check) and validate `main + pick` results in a single call, so a pick failure drops the
  whole season. ESPN and Yahoo already validate in one pass.
- **Record only onboarded seasons in `run()`.** Derive
  `onboarded_seasons = sorted({str(r["season"]) for r in raw_data})` after the fetch and
  pass that to `write_league_records(seasons=...)`. `upload_results_to_s3` already groups
  by the seasons present in `raw_data`, so its per-season files and manifest exclude
  skipped seasons with no change.

## Risks / Trade-offs

- [A season silently missing looks like data loss] → The skip is logged
  (`logger.warning` naming the dropped seasons) alongside the existing per-request error
  lines, so operators can see why a season is absent; the user simply sees the seasons
  that worked.
- [Latest/enumerating season must be reachable] → ESPN derives its season list from a
  synchronous fetch of the latest season; if that call `401`s the onboard still fails
  before any per-season fetch. This is pre-existing and out of scope; the reported bug has
  an accessible latest season.
- [Partial data reaching the processor] → Only fully-successful seasons produce S3 files,
  and the processor already processes per-season from the manifest, so no partially
  fetched season is ever processed.
