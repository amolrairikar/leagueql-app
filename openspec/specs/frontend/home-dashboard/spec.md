# home-dashboard Specification

## Purpose
The `/home` landing dashboard for a connected league. It summarizes the league at a glance: all-time standings (regular season and playoff), a championship timeline per owner, and headline stats (total matchups, total members, unique champions). Owner identities are stabilized across seasons and remapped through platform-migration mappings so a manager is counted consistently over time.

## Requirements

### Requirement: Show all-time summary
`/home` SHALL show all-time regular-season and playoff standings with owner-stable identities and colors, a championship timeline of winners'-bracket finals wins per owner, and headline stats.

#### Scenario: Dashboard summary
- **WHEN** a connected league's dashboard loads successfully
- **THEN** it shows all-time regular-season standings, playoff standings (counting only winners'-bracket games), a per-owner championship timeline, and headline stats (total matchups, total members, unique champions)

#### Scenario: Owner identity across migration
- **WHEN** the league has migrated platforms or has co-owners
- **THEN** owner IDs are remapped through the `PLATFORM_MIGRATION` mapping to the most recent team identity per owner, without double-counting co-owners

### Requirement: Render sparse leagues
The dashboard SHALL render correctly for a one-season or in-progress league, including when the seasons cookie has expired.

#### Scenario: Single/in-progress season
- **WHEN** the league has one season or an in-progress season
- **THEN** all-time tables and timeline render without error

#### Scenario: Expired seasons cookie
- **WHEN** the `leagueSeasons` cookie has expired (so `seasons` is `[]`) while `leagueId` persists
- **THEN** the stats grid renders three cards instead of four without crashing

### Requirement: Distinguish missing champions
A season with no champion SHALL show "TBD" only for the most recent season and "N/A" for a completed earlier season, neither counting toward totals.

#### Scenario: Champion status labels
- **WHEN** a season has no recorded champion
- **THEN** the most recent such season shows "TBD" (highlighted pending) and any earlier one shows "N/A" (not highlighted), and neither counts toward unique-champion or championship totals

### Requirement: Inline error on load failure
On a data-load failure the dashboard SHALL show one inline error in place of the summary sections, with no global error banner.

#### Scenario: Load failure
- **WHEN** the single league-data request fails
- **THEN** an inline `ErrorAlert` replaces the stats/champions/standings/chart sections rather than rendering empty tables, and no global error banner appears

### Requirement: Exclude unplayed matchups from dashboard stats

All-time standings and total-games statistics derived from matchups SHALL exclude unplayed
matchups — a matchup whose team scores are both exactly `0`.

#### Scenario: Unplayed matchup excluded from dashboard

- **WHEN** the matchups include an unplayed `0-0` week
- **THEN** all-time standings (games, wins/losses/ties, points) and the total-games stat count
  played matchups only
