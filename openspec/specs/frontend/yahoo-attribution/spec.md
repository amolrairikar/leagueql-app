# yahoo-attribution Specification

## Purpose
Attribution to Yahoo Fantasy, required by Yahoo's Fantasy Sports API terms, on every in-app page that displays a Yahoo league's data.

## Requirements

### Requirement: Show attribution for Yahoo leagues
When the active league's platform is Yahoo, every in-app page (each route rendered inside the shared app layout) SHALL end with a footer showing the official, unmodified Yahoo Fantasy logo and the text "Fantasy data provided by Yahoo Fantasy".

#### Scenario: Yahoo league
- **WHEN** a user views an in-app page for a Yahoo league
- **THEN** the page footer shows the Yahoo Fantasy logo and "Fantasy data provided by Yahoo Fantasy"

### Requirement: Link to Yahoo Fantasy
The attribution SHALL link to the official Yahoo Fantasy page `https://sports.yahoo.com/fantasy/`, opening in a new tab with `rel="noopener noreferrer"`.

#### Scenario: Attribution link
- **WHEN** the attribution footer is shown
- **THEN** it links to `https://sports.yahoo.com/fantasy/` with `target="_blank"` and `rel="noopener noreferrer"`

### Requirement: Hidden for other platforms
The attribution footer SHALL NOT render for ESPN or Sleeper leagues, or in demo mode.

#### Scenario: ESPN or Sleeper league
- **WHEN** a user views an in-app page for an ESPN or Sleeper league
- **THEN** no Yahoo attribution footer is shown

#### Scenario: Demo mode
- **WHEN** a user views an in-app page in demo mode
- **THEN** no Yahoo attribution footer is shown
