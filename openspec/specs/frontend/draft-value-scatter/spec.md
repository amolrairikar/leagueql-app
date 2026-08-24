# draft-value-scatter Specification

## Purpose
A free "Draft value" section on the `/draft_recap` page: a scatterplot of every drafted player with draft position (overall pick number) on the x-axis and season points on the y-axis, each dot colored by position. A position dropdown filters the dots and the page-level season selector drives which draft is shown. Computed entirely client-side from the season's `DRAFT` view.

## Requirements

### Requirement: Render the draft-value scatter
The Draft Recap page SHALL render a "Draft value" scatterplot below the draft board — one dot per scored pick for the selected season, x = draft position, y = season points, colored by position with a legend — recomputing on season change and rendering for everyone.

#### Scenario: Scatter render
- **WHEN** a season with draft data is selected
- **THEN** a scatterplot renders below the board with one dot per scored pick (x = `overall_pick_number`, y = `total_points`), colored by position from the shared palette, with a legend; switching the season selector recomputes it, and the section renders for everyone

#### Scenario: Dot tooltip
- **WHEN** a dot is hovered
- **THEN** its tooltip shows the player name, the drafting manager, points scored, and draft position

### Requirement: Plot only picks with finite axes
A pick SHALL be plotted only when both `total_points` and `overall_pick_number` are finite; a null `total_points` pick SHALL be omitted (never drawn at zero). A null player name falls back to a placeholder label.

#### Scenario: Missing scoring omitted
- **WHEN** a pick has a null/absent `total_points` (e.g. Sleeper D/ST and kickers)
- **THEN** it is omitted from the scatter rather than drawn at zero, so it forms no false floor of busts

#### Scenario: Missing player name
- **WHEN** a plotted pick has a null `player_name`
- **THEN** the tooltip falls back to a placeholder label and the dot still plots

### Requirement: Filter by position
A single dropdown SHALL offer "All positions" plus each present position (ordered by `FANTASY_POSITION_ORDER`), filter the plotted dots locally, and reset to "All positions" on mount without affecting the board.

#### Scenario: Position filter
- **WHEN** a position is selected in the dropdown
- **THEN** only that position's dots plot ("All positions" shows every dot); the filter is local, resets to "All positions" on mount, and does not affect the draft board

#### Scenario: Empty position filter
- **WHEN** a position with no scored picks is selected
- **THEN** an empty plot area renders rather than a crash

### Requirement: Handle load failures and empty data
A `DRAFT` load failure SHALL render an inline message and a season with no scored picks an empty-state message, never crashing.

#### Scenario: Failure or empty
- **WHEN** the `DRAFT` query fails (404/error) or the season has no scored picks
- **THEN** an inline message or empty-state message renders instead of a crash
