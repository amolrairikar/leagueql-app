## ADDED Requirements

### Requirement: Fetch ESPN box scores from the seasons endpoint
The onboarder SHALL request each week of ESPN matchups for seasons 2018 and later from the
`seasons/{season}/segments/0/leagues/{league_id}` endpoint with the `mBoxscore` and
`mMatchupScore` views and that week's `scoringPeriodId`, so each matchup carries its teams'
weekly rosters. Other ESPN data types for seasons up to 2018, and all data types for seasons
before 2018, SHALL be requested from the `leagueHistory/{league_id}?seasonId={season}` endpoint.

#### Scenario: 2018 matchups include box scores
- **WHEN** an ESPN league with a 2018 season is onboarded
- **THEN** each 2018 per-week matchup request uses the `seasons/2018/segments/0` endpoint, and
  the 2018 matchups' box scores list each team's starters and bench

#### Scenario: Other 2018 data still uses league history
- **WHEN** an ESPN league with a 2018 season is onboarded
- **THEN** the 2018 users, settings, draft picks, and player scoring totals requests use the
  `leagueHistory` endpoint

#### Scenario: Pre-2018 matchups unchanged
- **WHEN** an ESPN league with a 2017 season is onboarded
- **THEN** each 2017 per-week matchup request uses the `leagueHistory` endpoint
