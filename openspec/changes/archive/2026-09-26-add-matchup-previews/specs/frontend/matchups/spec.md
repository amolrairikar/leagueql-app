## MODIFIED Requirements

### Requirement: Open a box score
Opening a **played** matchup SHALL show both teams' starters and bench with per-player points.
Opening a **live-week (`0–0`, unplayed)** matchup SHALL instead show the matchup preview (see the
`frontend/matchup-previews` capability).

#### Scenario: Box score
- **WHEN** the user opens a played matchup
- **THEN** both teams' starters and bench are shown with per-player points

#### Scenario: Live-week matchup opens a preview
- **WHEN** the user opens a matchup whose two scores are both `0` (an unplayed, in-progress game)
- **THEN** the matchup preview is shown instead of the box score
