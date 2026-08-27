## ADDED Requirements

### Requirement: Demo bracket page offers a playoff-race toggle
In demo mode only, the Playoff Bracket page SHALL show a `Bracket / Playoff Race` toggle. Selecting `Playoff Race` SHALL replace the completed demo bracket with the playoff-race predictor in replay mode over the last three regular-season weeks; selecting `Bracket` SHALL return to the bracket. The demo dataset SHALL include a `LEAGUE_SETTINGS#{season}` bucket so the predictor can render its playoff cutoff. The toggle SHALL NOT appear outside demo mode.

#### Scenario: Toggle present in demo
- **WHEN** the Playoff Bracket page renders in demo mode for a completed demo season
- **THEN** a `Bracket / Playoff Race` toggle is shown alongside the bracket

#### Scenario: Switch to Playoff Race
- **WHEN** the user selects `Playoff Race` in demo mode
- **THEN** the playoff-race predictor renders over the last three regular-season weeks, sourcing its cutoff from the demo `LEAGUE_SETTINGS` bucket, and selecting `Bracket` returns to the bracket

#### Scenario: Toggle hidden outside demo
- **WHEN** the Playoff Bracket page renders for a real (non-demo) completed season
- **THEN** no `Bracket / Playoff Race` toggle is shown and the bracket renders as before
