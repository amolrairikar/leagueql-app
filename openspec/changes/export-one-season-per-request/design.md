# Design

## Context

`GET /leagues/{id}/export` returns a JSON bundle (`{data: {season: {view: rows[]}}}`) in a single
Lambda response, which Lambda caps at 6 MB. Multi-season bundles can exceed that (see proposal.md).
The dialog already merges the bundle into one ZIP via `downloadLeagueZip`, which derives seasons
from `Object.keys(bundle)`, and the backend already accepts a single season.

## Goals / Non-Goals

**Goals:**
- Keep each response well under 6 MB by requesting one season at a time.
- Keep the user-facing result unchanged: one ZIP, same file layout.

**Non-Goals:**
- Handling a single season larger than 6 MB (would need S3 presigned URLs).
- Backend, API contract, or per-season progress UI changes.

## Decisions

- **Frontend-only fan-out.** The dialog loops over selected seasons calling the existing
  `exportLeague(leagueId, platform, [season])`, then merges results with `Object.assign`. The
  alternative, a backend change (S3 presigned URL or a new per-season endpoint), is heavier and
  not needed while one season fits.
- **Bounded concurrency of 3** via a small inline worker pool (no new dependency). Fully parallel
  would fan out many Lambda invocations each using 8 read workers; sequential is slow for leagues
  with many seasons.
- **Abort on error, skip on 404.** Any non-404 failure aborts the export, matching the backend's
  fail-the-whole-export-on-read-error rule and avoiding a silently incomplete ZIP. A 404 means the
  season has no stored data, which previously was just omitted from a multi-season bundle, so it is
  skipped. If all seasons are skipped, an error is shown instead of an empty ZIP.
- **Single `exportedAt` timestamp** computed once before the requests, so the README and manifest
  stay consistent.

## Risks / Trade-offs

- [One season still exceeds 6 MB] → Surfaces as the same inline error; move to S3 presigned URLs if
  it occurs.
- [More requests per export] → Concurrency cap of 3 limits load; requests are skipCache GETs.
- [In-flight requests after an abort] → Remaining queued seasons are not started once one fails;
  already-running requests finish and their results are discarded.
