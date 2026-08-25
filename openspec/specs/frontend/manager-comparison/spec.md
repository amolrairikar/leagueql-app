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
Playoff appearances and championships SHALL be derived from the winners' bracket, with identities correct across migrated platforms.

#### Scenario: Playoff/championship derivation
- **WHEN** two managers are compared
- **THEN** playoff appearances (distinct seasons reaching the winners' bracket) and championships (winners'-bracket Finals wins) are derived, with owner identities remapped across platforms

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
