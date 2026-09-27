## ADDED Requirements

### Requirement: Freeze the Seed · Owner column in the projected standings
When the projected standings table scrolls horizontally (for example on a narrow mobile viewport),
its Seed · Owner column SHALL stay frozen at the left edge, header and rows alike, with an opaque
background that preserves the playoff-row highlight. On narrow (mobile) viewports the frozen column
SHALL be capped at a fixed width comparable to Season Standings' owner column, with long owner and
team names wrapping within it; from the `sm` breakpoint up it SHALL size to its content. The
playoff line's label SHALL likewise stay in view at the left edge.

#### Scenario: Owner column stays visible while scrolling
- **WHEN** the user scrolls the projected standings table horizontally
- **THEN** the Seed · Owner header and each row's seed and owner stay fixed at the left edge while
  the other columns scroll beneath them

#### Scenario: Playoff rows keep their highlight
- **WHEN** a frozen Seed · Owner cell belongs to a team currently in a playoff seed
- **THEN** it shows the same playoff highlight as the rest of its row, and the scrolled columns
  do not show through it

#### Scenario: Frozen column is capped on mobile
- **WHEN** the table is shown on a viewport narrower than the `sm` breakpoint and a team has a long
  owner or team name
- **THEN** the frozen Seed · Owner column stays at its capped width and the name wraps within it,
  leaving room for the scrolling columns

#### Scenario: Playoff line label stays in view
- **WHEN** the table is scrolled horizontally
- **THEN** the "Playoff line" label stays visible at the left edge
