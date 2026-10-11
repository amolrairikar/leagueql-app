## ADDED Requirements

### Requirement: Expand a season inline to show its schedule
On `/manager_history`, each season card with at least one played game SHALL expand in place, without opening a
modal, to show that manager's week-by-week schedule and results for the season. Clicking the card again SHALL
collapse it.

#### Scenario: Expanding a season shows its schedule inline
- **WHEN** the user clicks a season card that has played games
- **THEN** the card expands to show that season's schedule and results, and no dialog opens

#### Scenario: Clicking an expanded season collapses it
- **WHEN** the user clicks the header of an expanded season card
- **THEN** the card collapses and its schedule is hidden

#### Scenario: Several seasons stay expanded
- **WHEN** the user expands one season and then another
- **THEN** both seasons remain expanded at the same time

#### Scenario: Selecting a game shows its box score inside the season
- **WHEN** the user clicks a game in an expanded season's schedule
- **THEN** that game's box score is shown inside the same season card

#### Scenario: A season with no games cannot be expanded
- **WHEN** a season card has no played games
- **THEN** the card is not expandable
