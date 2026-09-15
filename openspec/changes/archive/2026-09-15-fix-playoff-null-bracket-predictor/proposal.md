## Why

For an early-season Sleeper league the `/playoff_bracket` page renders blank round
columns instead of the playoff-race predictor. Sleeper seeds its winners bracket with
concrete teams only for round 1; the championship and later rounds reference `t1_from`/
`t2_from` with null teams, and the processor drops entries whose `t1`/`t2` are null
(`src/processor/handler.py`). So the frontend receives only round-1 matches, all with
`winner: null` and `position: null`. Because `matches.length > 0`, `BracketContent`
skips the predictor handoff and tries to render a bracket that has no championship
(`position === 1`) and no semifinals — producing the blank round-column scaffold the
`frontend/playoff-bracket` spec explicitly forbids.

## What Changes

- Treat a bracket whose matches have neither a decided result (`winner`) nor a final
  placement (`position`) — a seeded-but-unplayed "null bracket" — as **no renderable
  bracket**, applying the same predictor / empty-state handoff already used for an empty
  bracket. The predictor self-gates (it shows the empty-state message when the regular
  season is already complete), so a legitimate seeded bracket awaiting its first playoff
  game still resolves to the correct empty-state message rather than blank columns.
- A bracket with at least one decided `winner` or a final `position` (a real,
  renderable bracket, including one seeded and in progress) is unaffected and renders as
  before, with unplayed matches shown as TBD.
- Add a frontend component scenario asserting the predictor renders for the latest
  in-progress season when the bracket query returns only null-result round-1 matches.

No API, DynamoDB, or backend behavior changes — this aligns the frontend empty-state
handoff with the existing spec's "never the blank round columns" guarantee.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `frontend/playoff-bracket`: Extend the "Empty-state for no bracket" requirement so a
  bracket whose matches carry no decided `winner` and no final `position` is treated as
  "no bracket to render" — the same trigger as an empty bracket for the predictor /
  empty-state handoff.

## Impact

- `frontend/src/features/playoff_bracket/playoff-bracket.tsx` — `BracketContent` routes
  to the predictor / empty-state when the bracket has no renderable data (no decided
  result and no placement), not only when `matches.length === 0`.
- `frontend/src/features/playoff_bracket/__tests__/` — new scenario + steps for the
  null-bracket → predictor path.
- No changes to `src/processor/handler.py` or any backend/data contract.
