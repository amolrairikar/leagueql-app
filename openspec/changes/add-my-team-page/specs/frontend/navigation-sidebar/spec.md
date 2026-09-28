# Spec Delta

## ADDED Requirements

### Requirement: My Team navigation entry
The sidebar SHALL always show a "My Team" entry linking to `/my_team`, placed directly below Home
and above Standings.

#### Scenario: Entry placed under Home
- **WHEN** the sidebar renders for a connected league
- **THEN** a "My Team" entry appears directly after "Home" and before "Standings", and it routes to `/my_team`
