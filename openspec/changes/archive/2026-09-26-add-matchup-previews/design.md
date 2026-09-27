## Context

`/matchups` (`frontend/src/features/matchups/matchups.tsx`) fetches the season's `MATCHUPS` view
(and `WEEKLY_STANDINGS`) and, per the recent week-filtering change, lists only played weeks plus
the current in-progress week. Live-week games are `0–0` placeholders (`isUnplayedMatchup` in
`@/lib/matchups`). The box score (`@/components/box-score-card`) is empty for those games.

The playoff-race predictor already models team scoring:
`frontend/src/features/playoff_race_predictor/compute-projection.ts` has (module-private)
`buildTeamScoring(playedRegMatchups)` → `Map<teamId, TeamScoring{mean, std, games}>` (own sample
σ with a pooled league-wide fallback) and `matchupWinProb(model, aId, bId)` (margin
`N(meanA−meanB, √(σA²+σB²))`, `Φ` via `normalCdf`, 0.5 fallback).

## Decisions

- **Reuse, don't duplicate, the scoring model.** Export `buildTeamScoring` and refactor the
  private `matchupWinProb(model, …)` into an exported `winProbability(scoring, aId, bId)` that
  takes the `Map<string, TeamScoring>` directly; update its one in-file caller to pass
  `model.teamScoring`. `normalCdf` stays private and is not copied. This keeps one source of truth
  for both the predictor and the preview.
- **No new fetches.** All preview data derives from the `MatchupItem[]` the page already loads.
  Records/PF/PA/high/weekly-series/recent-form/top-scorers are computed from a team's played,
  regular-season games; the scoring distribution and win probability come from the reused helpers.
  Records reflect games *entering* the live week because `0–0` placeholders are excluded.
- **Preview vs. box score is driven by the matchup, not the week.** A card is in preview mode when
  its matchup is unplayed (`teamA.score === 0 && teamB.score === 0`). Only the current week has
  such cards, so this naturally scopes the preview to the live week without threading week state.
- **Synchronous derivation, no extra Suspense.** The preview is built with `useMemo` from the
  already-resolved matchups inside `MatchupsContent`, mirroring how `BoxScoreView` renders inline;
  no new loading/skeleton boundary is needed.
- **Charts reuse existing infra.** The trend chart and the score-distribution curve both render
  through `@/components/ui/chart` (recharts), consistent with the season-standings and
  home-page charts; team colors come from the existing `avatarColor`/`colorMap`.
- **Top scorers are aggregated client-side.** No precomputed top-scorer view exists, so sum each
  starter's `points_scored` across the team's played games (prior art in
  `features/weekly_awards/compute-awards.ts`), and show the top few.

## Edge cases

- **Insufficient data (e.g. week 1, no played games):** `buildTeamScoring` returns `undefined`
  and `winProbability` falls back to `0.5`; the preview renders a 50/50 split, empty/short form
  and trend sections, and no projected/distribution collapse — all without error. This satisfies
  the existing `frontend/matchups` "Render sparse/in-progress data gracefully" requirement.
- **Byes / odd team counts:** a matchup always has two sides in `MatchupItem`; teams with no
  played games simply have empty derived series.

## Out of scope

- No backend, OpenAPI, DynamoDB, or architecture changes (no new deployed component).
- No new precomputed views; top scorers are not persisted.
