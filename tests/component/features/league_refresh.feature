Feature: League refresh reprocesses in place (BE-002, BE-013)
  A refresh re-runs the onboarder + processor for an already-onboarded league,
  overwriting precomputed views in place without duplicating them and without
  changing the global LEAGUE_COUNT.

  Scenario: Refreshing an onboarded Sleeper league overwrites views and keeps the count
    Given Sleeper player metadata and stats are cached in S3
    When the onboarder runs an ONBOARD for "SLEEPER" league "100" with fixture "sleeper/raw_data_2024.json"
    And the processor processes the onboarded league
    Then the LEAGUE_COUNT is 1
    And the league has exactly 3 "MATCHUPS#2024" item(s)
    When the onboarder runs a REFRESH for "SLEEPER" league "100" with fixture "sleeper/raw_data_2024.json"
    And the processor processes the onboarded league
    Then a JOB_STATUS "COMPLETED" exists for the job
    And the league has exactly 3 "MATCHUPS#2024" item(s)
    And the LEAGUE_COUNT is 1
