# draft-grades Specification

## Purpose
The `/draft_grades` page grades each manager's draft for a selected season and highlights steals and busts using the precomputed `draft_rank_delta` (drafted position rank vs actual end-of-season position rank). Steals massively outperformed their draft slot; busts are early picks who badly underperformed.

## Requirements

### Requirement: Grade each manager's draft
`/draft_grades` SHALL assign each manager an overall draft grade for the selected season, derived from their picks.

#### Scenario: Per-manager grade
- **WHEN** a season is selected
- **THEN** each manager is assigned an overall draft grade derived from their picks

### Requirement: Highlight steals and busts
The page SHALL flag steals (`draft_rank_delta >= 5`) and busts (`draft_rank_delta <= -5`, picked more than the round buffer before the last round, rounds 1–10).

#### Scenario: Steal and bust flags
- **WHEN** picks are classified
- **THEN** steals (`delta >= 5`) and busts (`delta <= -5`, beyond `BUST_ROUND_BUFFER`, within rounds 1–10) are highlighted

### Requirement: Tolerate null analytics and in-progress seasons
Picks with null rank/delta SHALL be excluded from steal/bust flags, null `vorp` for K/D/ST SHALL not error, and in-progress seasons SHALL render without crashing.

#### Scenario: Null analytics excluded
- **WHEN** a pick has null `actual_position_rank`/`draft_rank_delta` (e.g. missing stats)
- **THEN** it is excluded from steal/bust flags

#### Scenario: In-progress season
- **WHEN** end-of-season ranks are incomplete or `vorp` is null for K/D/ST
- **THEN** grading handles the nulls and renders provisionally without crashing
