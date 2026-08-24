# lineup-efficiency Specification

## Purpose
A free chip in the box score, below each team's name, answering "how many points did this manager leave on the bench?" For the team-week shown, it computes the optimal legal starting lineup from the combined `starters + bench` pool entirely client-side and compares it to what was actually started. The chip reads `⚡ {N}% efficient`; clicking it opens a Start/Sit Report of the slot-by-slot mistakes.

## Requirements

### Requirement: Show the efficiency chip in box scores
Each team in a box score with bench data SHALL show a lineup-efficiency chip below its name, rendering everywhere a box score appears (including demo mode), and nothing when bench data is unavailable.

#### Scenario: Chip shown
- **WHEN** a box score renders with bench data
- **THEN** each team shows a `{N}% efficient` chip below its name (for everyone, including demo mode)

#### Scenario: No bench data
- **WHEN** a box score has no bench data (e.g. ESPN seasons before 2018, or an empty bench)
- **THEN** no chip renders

### Requirement: Open the Start/Sit report
Clicking the chip SHALL open a Start/Sit Report listing each suboptimal slot (started vs optimal player and the point delta) and a points-left-on-the-bench footer, with a perfect-lineup state when nothing changed.

#### Scenario: Report contents
- **WHEN** the chip is clicked
- **THEN** the dialog lists slot rows with `delta > 0` (started vs optimal player, point delta) and a footer with total points left on the bench and the efficiency %

#### Scenario: Perfect lineup
- **WHEN** the actual lineup is already optimal
- **THEN** the chip shows 100% and the dialog shows the "Perfect lineup — nothing left on the bench" state

### Requirement: Compute the exact optimal lineup respecting slot eligibility
The optimizer SHALL derive the slot template from the actual starters' `fantasy_position`, respect FLEX/superflex eligibility, and find the true maximum via exact maximum-weight bipartite matching (not greedy), leaving a slot empty rather than starting a net-negative player.

#### Scenario: Overlapping flex slots
- **WHEN** the league has non-laminar flex slots (e.g. "RB/WR" overlapping "WR/TE")
- **THEN** the optimal lineup is the exact maximum-weight matching of slots↔players (min-cost max-flow), so it never under-counts the way a greedy slot-fill would

#### Scenario: Normalization and empty slots
- **WHEN** positions/slot labels vary by platform (`D/ST` vs `DEF`) or a slot's only eligible players score negative
- **THEN** labels are normalized via `POS_NORMALIZE` so either defense fills the slot, an unknown slot label matches only its own position, and a net-negative slot is left empty (0)

### Requirement: Report efficiency deltas consistently
Efficiency % SHALL be actual ÷ optimal clamped to [0,1] (100% when optimal is 0), points-left SHALL be optimal − actual (never negative), and the per-slot deltas SHALL sum to points-left.

#### Scenario: Metrics
- **WHEN** efficiency is computed
- **THEN** efficiency % = actual ÷ optimal (clamped, 100% when optimal is 0), points left = optimal − actual (≥ 0), and the report's per-slot deltas sum to points left
