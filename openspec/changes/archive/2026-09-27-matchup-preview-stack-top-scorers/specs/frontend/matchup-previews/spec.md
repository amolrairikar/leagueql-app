## MODIFIED Requirements

### Requirement: Top scorers
The preview SHALL show each team's top scoring players this season, aggregated from the team's
matchup starters. On narrow (mobile) viewports the two teams' lists SHALL be stacked vertically,
the left team's above the right team's; on wider viewports they SHALL be shown side by side.

#### Scenario: Top players per team
- **WHEN** the preview is shown for teams with played games
- **THEN** each team's top scoring players for the season are listed with their position and points

#### Scenario: Stacked on mobile
- **WHEN** the preview is shown on a viewport narrower than the `sm` breakpoint
- **THEN** the left team's top scorers are listed above the right team's, separated by a divider

#### Scenario: Side by side on wider screens
- **WHEN** the preview is shown on a viewport at or above the `sm` breakpoint
- **THEN** the two teams' top scorers are shown in two side-by-side columns
