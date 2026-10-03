# manager-comparison Specification

## Purpose
The `/manager_comparison` page compares any two managers head-to-head across all shared history: head-to-head record, points, playoff appearances, and championships. Owner identities are stabilized and remapped through platform migrations.

## Requirements

### Requirement: Compare two managers
The user SHALL be able to select two managers and see their head-to-head record and points, with self-comparison prevented or handled.

#### Scenario: Head-to-head comparison
- **WHEN** the user selects two distinct managers
- **THEN** their head-to-head record and points are shown

#### Scenario: Self-comparison
- **WHEN** the user selects the same manager twice
- **THEN** it is prevented or handled gracefully

### Requirement: Derive playoff appearances and championships
Playoff appearances SHALL be derived from the winners' bracket, and championships SHALL be counted from the seasons in which the manager's team carries the STANDINGS `champion = Yes` flag, with identities correct across migrated platforms.

#### Scenario: Playoff/championship derivation
- **WHEN** two managers are compared
- **THEN** playoff appearances (distinct seasons reaching the winners' bracket) and championships (seasons whose STANDINGS row has `champion = Yes`) are derived, with owner identities remapped across platforms

#### Scenario: Championship in a league whose final is not week 17
- **WHEN** a compared manager's team won a title game played in matchup period 15 and is marked
  `champion = Yes` in that season's standings
- **THEN** that season counts as one championship for the manager

### Requirement: Zero-state for no shared history
Managers with no shared matchups SHALL show a clear zero-state.

#### Scenario: Never played each other
- **WHEN** the two selected managers never played each other
- **THEN** the head-to-head shows a clear empty/zero record

### Requirement: Exclude unplayed matchups from head-to-head stats

Head-to-head records, win percentages, average points, and the game log SHALL exclude unplayed
matchups — a matchup whose team scores are both exactly `0` — so future placeholder games are not
counted as ties or listed in the log.

#### Scenario: Unplayed matchup excluded from comparison

- **WHEN** two managers have an unplayed `0-0` matchup scheduled
- **THEN** it is not counted in their records/win% and does not appear in the head-to-head game log

### Requirement: Equal-width comparison columns with horizontal scroll

The comparison grid SHALL give both managers' stat columns (header name, values, and bars) equal
width regardless of username length, and SHALL scroll horizontally within its own container
rather than compressing either manager's column when the equal-width columns do not fit the
viewport.

#### Scenario: Long username on a narrow viewport

- **WHEN** one selected manager's username is much longer than the other's and the viewport is
  too narrow to fit both columns at that width
- **THEN** both manager columns render at the same width, and the comparison grid scrolls
  horizontally within its container without widening the rest of the page

#### Scenario: Columns fit the viewport

- **WHEN** both manager columns fit within the available width
- **THEN** the columns split the available width equally and no horizontal scroll appears
