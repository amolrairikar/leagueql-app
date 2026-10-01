# Spec Delta

## MODIFIED Requirements

### Requirement: Select seasons to process
The processor SHALL recompute only the latest season on a normal refresh, every season in the manifest when `reprocess_all=true`, and exactly the listed seasons when the manifest carries `reprocess_seasons`.

#### Scenario: Normal refresh
- **WHEN** a normal refresh runs
- **THEN** only the latest season is recomputed (`resolve_seasons_to_process`)

#### Scenario: Reprocess all
- **WHEN** the manifest carries `reprocess_all=true`
- **THEN** the processor recomputes every season in the manifest from the raw season files already in S3

#### Scenario: Reprocess specific seasons
- **WHEN** the manifest carries `reprocess_seasons=2019`
- **THEN** the processor recomputes only season 2019 from the raw season files already in S3,
  regardless of the previous manifest's seasons

## ADDED Requirements

### Requirement: Merge backfilled Yahoo lineups into matchups
When processing a Yahoo season, the processor SHALL attach starter and bench lineups to each
matchup from the season's backfilled lineup store when one exists. Stored lineups SHALL take
precedence over any weekly rosters carried in the raw season file. Without either, the season's
matchups SHALL have empty lineups.

#### Scenario: Backfilled lineups attached
- **WHEN** a Yahoo season with a lineup store for weeks 1–14 is processed
- **THEN** each matchup in weeks 1–14 has starter and bench lineups with each player's weekly
  points, and each team's starter points add up to its matchup score

#### Scenario: Legacy in-file rosters still used
- **WHEN** a Yahoo season has weekly rosters in its raw season file and no lineup store
- **THEN** its matchups get lineups from the in-file rosters

#### Scenario: No lineups yet
- **WHEN** a Yahoo season has neither a lineup store nor in-file rosters
- **THEN** its matchups are written with empty starter and bench lineups and every other view is
  unaffected
