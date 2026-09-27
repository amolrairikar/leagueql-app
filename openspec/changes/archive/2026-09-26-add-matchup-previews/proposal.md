## Why

The `/matchups` page now shows only played weeks plus the current in-progress week, whose games
are `0–0` placeholders. Opening one of those live-week matchups shows an empty box score (no
player points yet), which is useless before kickoff. Managers want a **pre-game preview** that
compares the two teams so the live week's matchups are worth opening.

## What Changes

- Add a **matchup preview** for live-week (`0–0`) matchups on `/matchups`. Its card's action reads
  **"View matchup preview"** instead of "View box score", and opening it shows a head-to-head
  comparison instead of the (empty) box score.
- The preview shows: a **win-probability** split + single **projected score** per team and each
  team's **score-distribution** bell curve; a **head-to-head** stat comparison (Win%, Avg PF,
  Avg PA, scoring consistency σ, ceiling); **recent form** (last few results); a **points-by-week
  trend** chart vs. league average; and each team's **top scorers** this season.
- Played (past) matchups are unchanged — they still open the box score.
- On the live/unplayed week, the per-week award cards in the Weekly Awards section are **hidden**
  (no award can be determined for an unplayed week); the running week-to-date tally still renders.
- Add an entry to the in-app changelog describing the feature.

Everything is computed **client-side from the `MATCHUPS` view the page already fetches** — the
scoring-distribution and win-probability math is reused from the playoff-race predictor. No new
API, DynamoDB, or deployed infrastructure, so the architecture diagram and data-model docs are
unchanged.

## Capabilities

### New Capabilities
- `frontend/matchup-previews`: A pre-game head-to-head preview shown when a member opens a
  live-week (`0–0`) matchup on `/matchups` — win probability, projected score + distribution,
  head-to-head stats, recent form, a points-by-week trend, and top scorers, all derived from the
  season's matchups.

### Modified Capabilities
- `frontend/matchups`: A live-week (`0–0`) matchup opens the matchup preview; a played matchup
  still opens the box score.
- `frontend/weekly-awards`: The per-week award cards are hidden for an unplayed week (all `0–0`),
  since no award can be determined; the week-to-date tally still renders.

## Impact

- **Frontend:** new `frontend/src/features/matchups/compute-preview.ts` (pure derivations) and
  `frontend/src/features/matchups/matchup-preview.tsx` (the `MatchupPreviewCard`); wiring in
  `frontend/src/features/matchups/matchups.tsx` (live-card CTA + render the preview vs. box score);
  a small refactor in `frontend/src/features/playoff_race_predictor/compute-projection.ts` to
  export the reused scoring/win-probability helpers; hide the empty award-card grid for an
  unplayed week in `frontend/src/features/weekly_awards/weekly-awards.tsx`; new changelog entry in
  `frontend/src/features/changelog/constants.ts`.
- **Tests:** frontend component (`frontend/src/features/matchups/__tests__/`) and a compute unit
  test (`frontend/src/features/matchups/__tests__/compute-preview.test.ts`); re-run the
  playoff-predictor tests after the shared-helper refactor.
- **No backend, OpenAPI, DynamoDB, or infra/architecture changes.**
