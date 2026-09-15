Feature: League refresh reprocesses in place (backend/league-refresh)
  A refresh re-runs the onboarder + processor for an already-onboarded league,
  overwriting precomputed views in place without duplicating them.

  Scenario: Refreshing an onboarded Sleeper league overwrites views in place
    Given Sleeper player metadata and stats are cached in S3
    When the onboarder runs an ONBOARD for "SLEEPER" league "100" with fixture "sleeper/raw_data_2024.json"
    And the processor processes the onboarded league
    Then the league has exactly 3 "MATCHUPS#2024" item(s)
    When the onboarder runs a REFRESH for "SLEEPER" league "100" with fixture "sleeper/raw_data_2024.json"
    And the processor processes the onboarded league
    Then a JOB_STATUS "COMPLETED" exists for the job
    And the league has exactly 3 "MATCHUPS#2024" item(s)

  Scenario: A refresh within the weekly cooldown is rejected
    Given a LEAGUE_LOOKUP exists for league "200" platform "SLEEPER" canonical "canon-2"
    And league "canon-2" was last refreshed 2 days ago
    And the request is authenticated as "owner_user"
    When I POST a REFRESH of league "200" on "SLEEPER"
    Then the API responds with status 429
    And the API response detail contains "once per week"

  Scenario: An ESPN refresh is allowed when only unplayed later weeks are stored
    # ESPN pre-stores the full-season schedule, so weeks 11 and 18 exist as 0-0
    # rows while the latest played week (09) is behind current NFL state. The
    # up-to-date guard must judge "current" against the latest played week and let
    # the refresh proceed.
    Given a LEAGUE_LOOKUP exists for league "300" platform "ESPN" canonical "canon-3"
    And the current NFL state is season "2025" week "10"
    And league "canon-3" has a played matchup for season "2025" week "09"
    And league "canon-3" has an unplayed matchup for season "2025" week "11"
    And league "canon-3" has an unplayed matchup for season "2025" week "18"
    And the request is authenticated as "owner_user"
    When I POST a REFRESH of league "300" on "ESPN"
    Then the API responds with status 201
    And the onboarder Lambda was invoked
