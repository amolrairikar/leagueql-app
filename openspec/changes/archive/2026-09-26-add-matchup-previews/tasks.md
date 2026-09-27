## 1. Reuse the scoring / win-probability model

- [x] 1.1 In `frontend/src/features/playoff_race_predictor/compute-projection.ts`, export
  `buildTeamScoring` and refactor the private `matchupWinProb(model, aId, bId)` into an exported
  `winProbability(scoring: Map<string, TeamScoring> | undefined, aId, bId)`; update its in-file
  caller to pass `model.teamScoring`. Keep `normalCdf` private. Verify the existing
  playoff-predictor tests still pass (`npx vitest run src/features/playoff_race_predictor`).

## 2. Compute module

- [x] 2.1 Add `frontend/src/features/matchups/compute-preview.ts` with `TeamPreviewStats`
  (`wins/losses/ties/record/winPct/avgPf/avgPa/highScore`, `scoring?`, `weekly[]`, `recentForm[]`,
  `topScorers[]`) and `buildMatchupPreview(matchups, teamAId, teamBId): MatchupPreviewData`
  (both teams' stats, `winProbA/B`, `projA/B`, per-week `leagueAvg`). Derive everything from
  played, regular-season `MatchupItem`s (reuse `isUnplayedMatchup`, `isRegularSeason`,
  `buildTeamScoring`, `winProbability`). Aggregate top scorers from `team_*_starters`. Verify with
  the unit test in 5.2.

## 3. Preview component

- [x] 3.1 Add `frontend/src/features/matchups/matchup-preview.tsx` exporting `MatchupPreviewCard`
  (mirrors `BoxScoreCard`'s shell + `onClose`): hero with `TeamAvatar`s, records, win-probability
  split, single projected score, and per-team score-distribution curve; head-to-head comparison
  bars (reuse the dual-bar pattern + `pct` from `@/lib/utils`); recent form; points-by-week trend
  chart via `@/components/ui/chart`; top scorers with position chips (`positionColorMeta`). Team
  colors from `avatarColor`. Verify with the component test in 5.1.

## 4. Wire into the matchups page

- [x] 4.1 In `frontend/src/features/matchups/matchups.tsx`: make `MatchupCard` show "View matchup
  preview →" when the matchup is live (`teamA.score === 0 && teamB.score === 0`); thread the raw
  `MatchupItem[]` through `MatchupsData`; in `MatchupsContent`, render `<MatchupPreviewCard>` (via
  `useMemo(buildMatchupPreview(...))`) for a live selected matchup and `<BoxScoreView>` otherwise.
  Verify with the component test in 5.1.
- [x] 4.2 Prepend a new release entry to `CHANGELOG` in
  `frontend/src/features/changelog/constants.ts` with an "Added" bullet for matchup previews;
  verify `/changelog` renders it (existing changelog tests).
- [x] 4.3 In `frontend/src/features/weekly_awards/weekly-awards.tsx`, hide the per-week award-card
  grid when the active week has no computable awards (an unplayed `0-0` week); keep the tally.
  Verify with the weekly-awards component test.

## 5. Tests

- [x] 5.1 Extend `frontend/src/features/matchups/__tests__/matchups.feature` +
  `matchups.steps.test.tsx` with scenarios: live-week card shows "View matchup preview" and opens
  the preview (win probability, projected score + distribution, recent form, top scorers visible);
  a played matchup still opens the box score; an early-season/no-played-games week renders the
  preview gracefully (≈50/50, no crash). Provide multi-week `MATCHUPS` incl. a `0–0` current week
  (extend `src/test/fixtures.ts` or build inline). Verify `npx vitest run src/features/matchups`.
- [x] 5.2 Add `frontend/src/features/matchups/__tests__/compute-preview.test.ts` covering
  records/PF/PA/high, top-scorer aggregation, recent form, win probability, and the
  empty/insufficient-data path. Verify it passes.

## 6. Verification

- [x] 6.1 `npx @fission-ai/openspec@latest validate --all` is green.
- [x] 6.2 From `frontend/`: `npm run format:fix && npm run lint` are clean.
- [x] 6.3 From `frontend/`: `npx vitest run src/features/matchups src/features/playoff_race_predictor`
  (and `npm run test`) pass.
- [x] 6.4 Manual: run the app, open `/matchups` on a live-week league — the current-week card reads
  "View matchup preview" and opens the preview; past weeks still open the box score; check both
  themes and phone width.
