## MODIFIED Requirements

### Requirement: Show weekly award cards
`/matchups` SHALL render one card per award type for the selected week below the matchup grid,
recomputing on week navigation, and rendering for everyone — except when the selected week has no
computable awards (an unplayed/in-progress week whose games are all `0-0`), in which case the
award cards are hidden while the week-to-date tally still renders.

#### Scenario: Award cards
- **WHEN** a played week is selected on `/matchups`
- **THEN** cards render for Highest Score, Lowest Score, Biggest Blowout, Narrowest Win, Best Loss, and Worst Win for that week, recomputing when navigating to a different week; the section renders for everyone

#### Scenario: No eligible winner
- **WHEN** a week has awards but an individual award type has no computable winner (e.g. every game tied)
- **THEN** that card shows an em dash and "No award this week" rather than a blank

#### Scenario: Unplayed week hides the award cards
- **WHEN** the selected week is unplayed (its matchups are all `0-0`), so no award can be determined
- **THEN** the per-week award cards are hidden and only the week-to-date tally is shown
