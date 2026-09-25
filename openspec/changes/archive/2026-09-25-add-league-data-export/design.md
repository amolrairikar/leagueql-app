## Context

See proposal.md — Why. The processed views this exports already exist in DynamoDB under
`PK = LEAGUE#{canonical_league_id}` and are served one-at-a-time by `GET /leagues/{leagueId}/query`
(`src/api/routes.py` `query_league`). Views are either a single item per season
(`STANDINGS#{season}`, `WEEKLY_STANDINGS#{season}`, `DRAFT#{season}`, `PLAYOFF_BRACKET#{season}`,
`LEAGUE_SETTINGS#{season}`), a season-scoped prefix set (`MATCHUPS#{season}#WEEK#..`,
`TRANSACTIONS#{season}#{chunk}`), or a single all-seasons item (`TEAMS`). Membership is enforced by
`require_league_member` in `src/api/helpers.py`. The frontend has no ZIP or file-download utility
today, and no reusable Checkbox component (existing checkboxes are raw `<input type="checkbox">`).

## Goals / Non-Goals

**Goals:**
- One request returns every available view for the selected seasons, reusing the existing read and
  authorization logic.
- The download preserves the nested shape of the processed data (matchup starters/bench, draft
  picks), which JSON does and CSV does not.
- No new deployed infrastructure.

**Non-Goals:**
- Exporting raw S3 payloads (only processed DynamoDB views are exported).
- Letting the user pick individual views (all available views are included per selected season).
- Server-side ZIP construction / streaming for very large leagues (see Risks).

## Decisions

- **New endpoint vs. client fan-out over `/query`.** A dedicated `GET /leagues/{leagueId}/export`
  does the fan-out server-side in one round trip and one auth check. Client fan-out would need many
  requests (views × seasons) and re-filtering of unsuffixed all-season views on the client. Chosen:
  dedicated endpoint.
- **Backend returns JSON; frontend builds the ZIP.** The endpoint returns a plain JSON bundle;
  the browser assembles the ZIP with **jszip** and triggers the download. This avoids binary/base64
  responses through API Gateway + Lambda and keeps the endpoint a normal JSON read. Alternative
  (server builds the ZIP, returns binary) adds API Gateway binary-media and Lambda base64 handling
  for no real benefit here.
- **Extract a shared view-read helper.** The exact-`get_item` vs. paginated `begins_with`-concat
  logic currently inline in `query_league` is extracted into a helper in `src/api/helpers.py` and
  reused by both `query_league` and `export_league`. Non-behavioral for the query endpoint, so no
  spec change there.
- **Access = member, not owner.** Export is a read, so it uses `require_league_member` (matching
  `/query`) and the sidebar entry sits with the member-visible actions, not the owner-gated block.
- **Format = ZIP of JSON files.** Confirmed with the user; one `<season>_<view>.json` per view per
  season. Keeps nested structures intact and separates files for easy inspection.

## Risks / Trade-offs

- **Large payloads** → A member with many seasons of matchups + transactions could produce a bundle
  approaching API Gateway's ~10MB / Lambda's ~6MB sync response limits. Mitigation for v1: this is
  well within limits for typical leagues; the UI lets users export fewer seasons at a time. Chunked
  streaming/pagination is deferred (Non-Goal) and can be added later without changing the download
  format.
- **New frontend dependency (jszip)** → Small, widely used, MIT-licensed; added to
  `frontend/package.json`. Trade-off accepted to keep the backend returning plain JSON.
- **Refactor touches `query_league`** → Mitigated by keeping the extracted helper behavior-identical
  and relying on the existing `TestQueryLeagueEndpoint` suite to catch regressions.
