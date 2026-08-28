# Trade rest-of-season points

## Why
On `/transactions`, a trade shows only *what each side received* — player names and positions,
plus any traded picks. It never shows how the trade actually played out, which is the first thing
a manager wants to know when revisiting a deal. Adding the fantasy points each acquired player
went on to score lets the page answer "who won this trade?".

The data already exists: the `MATCHUPS` precomputed view holds per-player, per-week
`points_scored` (starters + bench) for the whole season, and the frontend can already fetch every
week of a season in one call (`getSeasonMatchups`, which queries `MATCHUPS#{season}#`). So the
feature is entirely client-side — no new backend view, no processor change, no backfill.

## What Changes
- **Per-player rest-of-season (ROS) points on trades:** each acquired player in a two-team trade
  shows the total fantasy points they scored from the trade's week onward (all games, started or
  benched; following the player regardless of later roster moves). Traded draft picks show no
  points.
- **Per-side total and winner:** each trade side shows the sum of its acquired players' ROS
  points, the higher-scoring side is marked, and the card shows the margin (or "Even" on a tie).
- **Graceful degradation:** the trade renders in its current form (no ROS additions, no error
  banner) when the season's matchup box scores are unavailable (e.g. a season with no matchups).
- **Known limitation:** `MATCHUPS` only covers players rostered by some league team each week, so
  weeks a traded player sits in free agency count as 0. Acceptable — traded players are almost
  always rostered.

This is Sleeper-only (ESPN exposes no transactions) and adds no new API field — points are
derived on the client from the existing `TRANSACTIONS` and `MATCHUPS` views.

## Impact
- Affected specs: `frontend/transactions` (new requirement: trade rest-of-season points).
- Affected code: `frontend/src/features/transactions/transactions.tsx` and `api-calls.ts`, and
  the component tests under `frontend/src/features/transactions/__tests__/`.
- No backend, DynamoDB, OpenAPI, or architecture-diagram changes.
