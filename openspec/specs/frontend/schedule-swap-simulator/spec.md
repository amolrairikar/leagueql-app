# schedule-swap-simulator Specification

## Purpose
A free section on the `/standings` page answering "what would each team's record be under another manager's schedule?" For the selected season it renders an N×N matrix, computed entirely client-side from the regular-season `MATCHUPS` view: rows are each team's own weekly scores (fixed), columns are each manager's schedule, and a cell is the row team's win total under the column manager's opponents. The diagonal reproduces each team's actual record.

## Requirements

### Requirement: Render the schedule-swap matrix
`/standings` SHALL render a matrix for the selected season with one row and one column per team, recomputing when the season selector changes, and rendering for everyone.

#### Scenario: Matrix render
- **WHEN** a season is selected on `/standings`
- **THEN** an N×N matrix renders with one row/column per team; switching the season selector recomputes it, and the section renders for everyone

### Requirement: Reproduce actual records on the diagonal
Each diagonal cell (`row === col`) SHALL equal that team's actual regular-season record and be visually highlighted.

#### Scenario: Diagonal
- **WHEN** the matrix renders
- **THEN** each team's diagonal cell equals its actual regular-season `W-L-T` record (ties counted) and is highlighted

### Requirement: Compute swapped records with self-matchup substitution
An off-diagonal cell SHALL equal the row team's win total under the column manager's schedule, using the row team's own scores, and facing the schedule's owner when the borrowed schedule would pit it against itself. Only regular-season games count.

#### Scenario: Off-diagonal cell
- **WHEN** cell `[R, C]` is computed
- **THEN** it iterates the weeks `C` played (regular season only), compares `R`'s actual weekly score against the opponent `C` faced — substituting `C` itself when `C` faced `R` — and byes (a missing score) are skipped

### Requirement: Color-scale cells
Cells SHALL be color-scaled relative to the row team's actual wins (more wins greener, fewer redder).

#### Scenario: Color scale
- **WHEN** a cell's swapped win total is compared to the row team's actual wins
- **THEN** it is colored greener for more wins and redder for fewer

### Requirement: Handle sparse data and load failures
The section SHALL render an empty-state message for fewer-than-two teams or no regular-season data, and an inline message on a `MATCHUPS` load failure, never crashing.

#### Scenario: Sparse or failed data
- **WHEN** the season has fewer than two teams / no regular-season data, or the `MATCHUPS` query fails (404 or error)
- **THEN** an empty-state or inline message renders instead of a crash or empty grid

### Requirement: Exclude unplayed matchups from simulation

The schedule-swap simulation SHALL exclude unplayed matchups — a matchup whose team scores are
both exactly `0` — so simulated records replay only played weeks.

#### Scenario: Unplayed matchup excluded from simulation

- **WHEN** the season's matchups include an unplayed `0-0` week
- **THEN** the simulated records for every schedule are computed from played weeks only
