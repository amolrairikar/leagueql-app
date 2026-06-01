# Code Repetition Findings

Review of `src/` for duplicated logic that could be consolidated. Criticality reflects
a combination of how much code is duplicated, how many copies exist, and the risk that
the copies drift out of sync (causing inconsistent behavior or bugs that are fixed in
one place but not others).

| Finding ID | Criticality | Rationale |
|------------|-------------|-----------|
| F-01 | High — ✅ Remediated | `JsonFormatter` + `setup_logger()` were copy-pasted into **6 modules**: `player_metadata/utils.py`, `sleeper_refresh/utils.py`, `onboarder/utils.py`, `processor/utils.py`, `sleeper_player_stats_refresher/utils.py`, and `api/main.py`, and had already diverged (correlation_id present/absent, `logger.handlers = [handler]` vs `if not logger.handlers`, root vs named `"leagueql"` logger). **Resolved** by `src/common/logging_utils.py` (unified on the root logger + a single shared `correlation_id_var`); all 6 modules now import/re-export from it. `build_lambda_zip.sh` vendors `src/common/` into every zip; shared tests live in `tests/unit/common/test_logging_utils.py`. |
| F-02 | High — ✅ Remediated | `publish_failure()` (SNS alert) was duplicated nearly verbatim in `onboarder/utils.py`, `processor/utils.py`, and `api/helpers.py`, differing only by the `Subject` string, with the client-init guard repeated too. **Resolved** by `src/common/sns.py` (single SNS client from `SNS_TOPIC_ARN`, no-op when unset; `publish_failure(error_message, subject)`); each service binds its subject via `functools.partial`. Shared behavior tested in `tests/unit/common/test_sns.py`; the API retains one test asserting its subject binding. Closed the prior `processor/utils.py` coverage gap (50% → 100%). |
| F-03 | High — ✅ Remediated | The Sleeper "walk the `previous_league_id` chain" loop was implemented twice in `onboarder/sleeper_client.py` (`resolve_sleeper_canonical_league_id()` and `SleeperClient._get_league_seasons()`), each with its own `MAX_CHAIN_DEPTH` guard, fetch, `raise_for_status`, and stop-at-`"0"` logic. **Resolved** by a shared `_iter_sleeper_league_chain()` generator that yields each league's API data; both callers now consume it and supply only their per-node action. Added a depth-limit test; chain-walk code fully covered (the remaining `sleeper_client.py` gaps are pre-existing async `fetch_all`/`_fetch` paths). |
| F-04 | Medium — ❌ Cancelled | NFL-state fetch against `https://api.sleeper.app/v1/state/nfl` is reimplemented in 4 places: `player_metadata/handler.py:fetch_nfl_state`, `sleeper_player_stats_refresher/handler.py:fetch_nfl_state`, `sleeper_refresh/utils.py:get_nfl_state`, and `api/helpers.py:get_nfl_state`. **Won't fix:** the differences encode genuinely different intent, not drift — `player_metadata` and `api` are **fail-open** (a failed fetch should let the operation proceed/skip a guard), while `sleeper_refresh` and `stats_refresher` are **fail-closed** (a failed fetch should abort, via 502 / `RuntimeError`). Secondary differences (retry-session vs bare `requests`, `timeout=10` vs `(5,10)`) align with those policies. Centralizing would force one error policy and change behavior at some call sites, so the duplication is left in place deliberately. |
| F-05 | Medium — ✅ Remediated | `build_retry_session()` was byte-for-byte identical in `player_metadata/utils.py` and `sleeper_player_stats_refresher/utils.py`. **Resolved** by `src/common/http.py`; both `utils.py` files now collapse to re-exports of `build_retry_session` + `logger`. Covered by `tests/unit/common/test_http.py`. |
| F-06 | Medium — ✅ Remediated | The fetch orchestration (`Semaphore(10)` + `asyncio.gather(..., return_exceptions=True)`) and the matchups week-range (`range(1,19) if season >= EXTENDED_SEASON_CUTOFF else range(1,18)`) were structurally duplicated between `onboarder/espn_client.py` and `onboarder/sleeper_client.py`. **Resolved** by two focused helpers in `onboarder/utils.py` — `run_fetches(session, url_data_list, fetcher)` and `matchup_weeks(season)` — used by both clients' `fetch_all`/`_build_all_request_urls`. Preferred focused helpers over a base class because the clients' `fetch_all` genuinely differ (ESPN cookies; Sleeper's second draft-pick round). New tests cover both helpers, including the gather-exceptions path. |
| F-07 | Medium — ❌ Cancelled | The recursive Decimal↔float walkers are inverse copies of the same shape: `processor/handler.py:sanitize_value` (float→Decimal) and `api/helpers.py:convert_decimals` (Decimal→float). **Won't fix:** the shared recursion skeleton is real, but each function is ~5 lines, they live in different Lambdas (so the helper would have to go in `common/` and be vendored — real packaging weight to save a few lines), and a higher-order `deep_map(value, transform)` is arguably less readable than the explicit inverse pair. Both functions are stable, so the "fix the recursion once" benefit is largely theoretical. Marginal payoff vs. abstraction/packaging cost; left as-is. |
| F-08 | Medium — ✅ Remediated | Sleeper player name/position building was repeated 3× in `processor/handler.py` (not `utils.py` as originally noted): `compile_sleeper_starter_stats`, `compile_sleeper_bench_stats`, and `compile_sleeper_player_scoring_totals` each computed `full_name` via `(meta.get("first_name") or "") + " " + (meta.get("last_name") or "")).strip()` and normalized position via `"D/ST" if position_raw == "DEF" else position_raw`. **Resolved** by a `sleeper_player_display_fields(meta) -> (full_name, position)` helper used by all three; covered by a dedicated test class. |
| F-09 | Medium — ✅ Remediated | The onboarder Lambda async-invoke payload (`body`/`requestType`/`canonicalLeagueId`/`correlation_id` + `InvocationType="Event"`) was constructed in 3 places: `sleeper_refresh/utils.py:invoke_onboarder_lambda`, `api/routes.py:onboard_league`, and `api/routes.py:migrate_league`. **Resolved** by `src/common/onboarder_invoke.py:invoke_onboarder(lambda_client, function_name, body, request_type, canonical_league_id, correlation_id)`; all three call sites pass only their per-request `body`. Callers keep their own status/error handling. Covered by `tests/unit/common/test_onboarder_invoke.py`. |
| F-10 | Low — ❌ Cancelled | The DynamoDB `LEAGUE_LOOKUP` Put item (PK/SK/`canonical_league_id`/`seasons`/`platform`/`league_id`) is written out 3× inside `onboarder/writer.py:write_onboarding_status_to_dynamodb` (MIGRATE, REFRESH-new-season, ONBOARD branches). **Won't fix:** low-value churn — the repetition is confined to one function, and an item-builder doesn't meaningfully improve clarity. Left as-is. |
| F-11 | Low — ❌ Cancelled | The DynamoDB "query all pages" loop (`while True: query(**kwargs); extend; ExclusiveStartKey`) appears in `api/helpers.py:_query_all_keys`, `api/routes.py:query_league`, and `sleeper_refresh/utils.py:get_sleeper_leagues`. **Won't fix:** the three loops differ in what they accumulate (key dicts vs full items vs grouped league records) and span two Lambdas; a shared paginator's marginal benefit doesn't justify the abstraction/packaging cost. Left as-is. |
| F-12 | Low — ❌ Cancelled | Sleeper base/state URLs are scattered as per-file constants (`SLEEPER_BASE_URL`, `SLEEPER_NFL_STATE_URL`, `SLEEPER_STATE_URL`, `SLEEPER_PLAYERS_URL`, `SLEEPER_STATS_URL`) across `sleeper_refresh`, `onboarder`, `player_metadata`, `sleeper_player_stats_refresher`, and `api`. **Won't fix:** these are stable, rarely-changing constants; centralizing them across 5 Lambdas adds `common/` coupling for little practical gain. Left as-is. |
| F-13 | Low — ❌ Cancelled | S3 "get object → `json.loads(body)`" is repeated in `processor/handler.py:read_s3_object` (not `utils.py`), the processor manifest read, and `sleeper_player_stats_refresher/handler.py`. **Won't fix:** the manifest read also needs the response `Metadata` (correlation_id) so it can't reuse a body-only helper, leaving only two ~3-line sites across two Lambdas — not enough to justify a vendored `common/` helper. Left as-is. |

## Note on the shared-code constraint

These Lambdas appear to be packaged independently (each has its own `requirements.txt` and
its own `utils.py`), so "shared module" remediation requires a distribution mechanism. F-01,
F-02, F-04, and F-05 (cross-Lambda duplication) are the candidates that need one; F-03 and
F-06–F-13 are within a single deployable unit and can be refactored with no packaging changes.

## Recommendation: shared `common/` folder vendored at build time (not a Lambda layer)

**Recommended approach: a `src/common/` package vendored into each function's zip by
`scripts/deployment_scripts/build_lambda_zip.sh`.** For this repo it is clearly the better
fit than a Lambda layer. Reasoning:

| Dimension | Vendored `common/` folder | Lambda layer |
|-----------|---------------------------|--------------|
| Build-script change | ~2 lines — copy `src/common/` into each `BUILD_DIR` alongside the existing `*.py` copy step | New publish/versioning pipeline outside the current zip flow |
| Multi-region | Works as-is; the zip is uploaded to both `-east-` and `-west-` buckets already | Layers are **region-scoped ARNs** — must publish + track a separate layer version in `us-east-1` and `us-west-2` |
| Version skew | None — each zip carries the exact `common/` code from that build; function and shared code are always in lockstep | Updating shared code means publishing a new layer version **and** repointing every function's ARN; easy to leave a function on a stale version |
| Local dev / tests | Imports resolve normally (`from common.logging_utils import logger`); no `/opt/python` shim needed | Layer code lives at `/opt/python` at runtime only; tests need extra path setup |
| Zip size cost | Negligible — shared code is pure-Python (logging, retry session, SNS publish, URL constants) with no heavy deps | Smaller function zips, but that saving only matters for large/binary shared deps, which these are not |
| Independent deployability | Preserved — each function zip is fully self-contained | A function now depends on the correct layer version also being deployed |

Layers earn their keep when the shared payload is large or has heavy binary dependencies and
you want to avoid re-uploading it per function. Here the shared code is small, pure-Python,
and the project already deploys to two regions — so the layer's cross-region ARN management
and version-skew risk outweigh its modest zip-size savings.

### Concrete shape

1. Create `src/common/` as a package (e.g. `logging_utils.py`, `http.py`, `sns.py`,
   `constants.py`). Use a package dir rather than flat files so the shared `logging_utils.py`
   does **not** collide with each function's own top-level `utils.py` when copied into the zip.
2. Functions import via the package, e.g. `from common.logging_utils import logger`.
3. In `build_lambda_zip.sh`, after the existing "Copy Python source files" step (which copies
   `*.py` at `-maxdepth 1`), add a copy of the shared package into the build dir:

   ```bash
   # Copy shared common package (vendored into every function zip)
   COMMON_DIR="$(dirname "$SOURCE_DIR")/common"
   if [[ -d "$COMMON_DIR" ]]; then
       cp -R "$COMMON_DIR" "$BUILD_DIR/"
   fi
   ```

   This lands `common/` at the zip root next to the handler, so `import common.*` resolves at
   runtime. No changes to the dependency install, OTEL config copy, or upload steps are needed.
4. If any shared module needs third-party deps (none of F-01/F-02/F-04/F-05 do beyond
   `requests`, which the relevant functions already vendor), add them to each consuming
   function's `requirements.txt`.

### Updating unit tests

Tests mirror the source layout (`tests/unit/<function>/`) and the repo rule is **do not
modify `sys.path`** — modules that share filenames are loaded with
`importlib.util.spec_from_file_location` and registered in `sys.modules` (see existing
`conftest.py` files). The shared package must follow the same pattern.

1. **Add a dedicated `tests/unit/common/` directory** mirroring `src/common/`, with one
   `test_<module>.py` per shared module (`test_logging_utils.py`, `test_http.py`,
   `test_sns.py`, `test_constants.py`). Test the shared functions **once, here, against
   `src/common/` directly** — do not re-test them inside each function's test folder.

2. **Delete the now-duplicated tests** from the per-function suites as their source moves to
   `common/`. For example, the logger / `build_retry_session` / `publish_failure` assertions
   currently living in `tests/unit/sleeper_refresh/test_utils.py`,
   `tests/unit/onboarder/test_utils.py`, `tests/unit/api/test_utils.py`, etc. collapse into
   the single `tests/unit/common/` suite — matching the de-duplication being done in `src/`.

3. **Bootstrap `common` in each consuming function's `conftest.py`** so the function modules'
   `import common.logging_utils` resolves at test time. Load it as a package via `importlib`
   and register it in `sys.modules` *before* loading the function modules — no `sys.path`
   edits:

   ```python
   import importlib.util
   import sys
   from pathlib import Path

   _COMMON = Path(__file__).parents[3] / "src" / "common"

   def _load_pkg(name: str, pkg_dir: Path) -> None:
       """Register src/common as an importable package in sys.modules."""
       spec = importlib.util.spec_from_file_location(
           name, pkg_dir / "__init__.py",
           submodule_search_locations=[str(pkg_dir)],
       )
       mod = importlib.util.module_from_spec(spec)
       sys.modules[name] = mod
       spec.loader.exec_module(mod)
       for sub in ("logging_utils", "http", "sns", "constants"):
           sub_path = pkg_dir / f"{sub}.py"
           if sub_path.exists():
               sub_spec = importlib.util.spec_from_file_location(
                   f"{name}.{sub}", sub_path
               )
               sub_mod = importlib.util.module_from_spec(sub_spec)
               sys.modules[f"{name}.{sub}"] = sub_mod
               sub_spec.loader.exec_module(sub_mod)

   # In the session-scoped autouse bootstrap, before loading handler/utils:
   _load_pkg("common", _COMMON)
   ```

4. **Coverage:** keep the suite near the 100% line/branch target the repo expects. Because
   the shared code is now exercised by `tests/unit/common/`, run coverage over both the
   function and the shared package, e.g. `pipenv run pytest tests/unit/ --cov=src
   --cov-report=term-missing` (the existing `--cov=src` already includes `src/common`).
