## Why

The playoff-race predictor shows a projected standings table, a playoff-odds column, and a
"clinched" ✓, but it never spells out *what has to happen* — the plain-language lines managers
actually track down the stretch: "win and you're in", "a loss ends it", "you're in unless you get
out-scored". The standings answer "where do things stand"; they don't answer "what does this
week's game mean for me".

## What Changes

- Add a **Clinching Scenarios** section directly below the projected-standings table. It lists
  **only teams still in contention whose next un-picked game is decisive**: winning it clinches a
  top-`num_playoff_teams` seat in every remaining outcome (**win & in**), losing it eliminates the
  team in every remaining outcome (**must win**), or both (**controls its own destiny**).
- Scenarios are computed **exactly** over the same enumeration of un-picked outcomes the playoff
  odds already use, and are **conditional on the user's picks**.
- Tiebreaks are handled rigorously. A berth counts as **clinched only when record alone secures
  it**; teams already clinched or already eliminated are **excluded** from the list (they are
  conveyed by the standings). Because points-for keeps accumulating in the games still to play, a
  same-record tie is never assumed decided: when a listed team's seat can come down to such a tie,
  the scenario states the **points-for margin** versus the rival(s) it must hold off.
- Add a one-line note distinguishing the odds column (how *likely*) from the scenarios (what is
  mathematically *guaranteed*). The odds column itself is **unchanged** here.
- Included in demo (replay) mode automatically, since the section lives in the shared predictor
  tool and the demo dataset already provides the settings/matchup data it needs.

## Capabilities

### Modified Capabilities
- `frontend/playoff-race-predictor`: the projected-standings view gains a clinching-scenarios
  section that surfaces, for teams still in contention, whether a win clinches / a loss eliminates
  their next game, with an explicit points-for margin for seats that could come down to a
  same-record tie — computed exactly over the un-picked outcomes and conditional on the user's
  picks.

## Impact

- **Frontend only.** No backend / API / DynamoDB / infrastructure / architecture-diagram change.
- `frontend/src/features/playoff_race_predictor/compute-projection.ts`: new pure
  `computeClinchScenarios` (new exported types), reusing the `computePlayoffOdds` enumeration
  setup and the `compareRecords` seeding. Clinched/eliminated (for exclusion) are derived from the
  enumeration; the row ✓ (wins-alone `computeClinched`) is left unchanged.
- `frontend/src/features/playoff_race_predictor/playoff-race-predictor.tsx`: new `ClinchScenarios`
  component rendered below `StandingsTable`, plus a one-line odds-vs-scenarios explainer.
- Tests: `compute-projection.test.ts` unit coverage (win-and-in with tie margins, must-win,
  controls-destiny, clinched/eliminated excluded, feasibility gate, pick-aware transitions), a
  jest-cucumber scenario, and demo/replay coverage.
- **Follow-up (separate change, out of scope):** rebuild the playoff-odds column onto a
  scoring-distribution Monte Carlo (weekly score ~ N(mean, σ)) so odds and scenarios agree exactly;
  that will modify the existing playoff-odds requirement, so it is deliberately not bundled here.
