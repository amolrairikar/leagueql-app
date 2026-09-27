## ADDED Requirements

### Requirement: Horizontally scroll overflowing matchups
The predictor's pickable matchups SHALL be horizontally scrollable when they are wider than the
available width (for example long owner or team names on a narrow mobile viewport), rather than
clipping them off-screen. Every team card (avatar, owner/team name, and record) across the week's
matchups SHALL be the same width on every viewport, sized to fit the widest card when the
matchups overflow.

#### Scenario: Long names scroll instead of clipping
- **WHEN** the predictor is shown on a viewport too narrow to fit a matchup's team names
- **THEN** the matchups can be scrolled horizontally to reveal the full names

#### Scenario: Team cards stay equal width on mobile
- **WHEN** the matchups overflow a narrow viewport and one team's name is longer than the others
- **THEN** every team card in the week is the same width, matching the widest card, as on desktop

#### Scenario: Matchups that fit do not scroll
- **WHEN** the week's matchups fit within the available width
- **THEN** they fill the available width and show no horizontal scrollbar
