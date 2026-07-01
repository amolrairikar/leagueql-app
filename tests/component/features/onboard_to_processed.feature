Feature: Onboard-to-processed pipeline (BE-001, BE-004)
  Drives the onboarder and processor as one component with the platform API
  mocked. The onboarder writes raw data to (moto) S3 and league records to
  DynamoDB; a synthesized S3 event then runs the processor, whose DuckDB
  transforms build the precomputed views read by the API.

  Scenario: A Sleeper league onboards end to end and builds every view
    Given Sleeper player metadata and stats are cached in S3
    When the onboarder runs an ONBOARD for "SLEEPER" league "100" with fixture "sleeper/raw_data_2024.json"
    Then the onboarder returns status 200
    And a LEAGUE_LOOKUP exists for onboarded league "100" platform "SLEEPER"
    And a METADATA item exists for the onboarded league
    When the processor processes the onboarded league
    Then a JOB_STATUS "COMPLETED" exists for the job
    And the recap generator was invoked after processing
    And the league has at least one "TEAMS#2024" item
    And the league has at least one "MATCHUPS#2024" item
    And the league has at least one "STANDINGS#2024" item
    And the league has at least one "WEEKLY_STANDINGS#2024" item
    And the league has at least one "PLAYOFF_BRACKET#2024" item
    And the league has at least one "DRAFT#2024" item
    And the league has at least one "TRANSACTIONS#2024" item
    And the standings show "Team Alice" as champion
    And the LEAGUE_COUNT is 1
    # BE-019: only the two completed transactions are stored (the failed waiver is dropped).
    When I GET "/leagues/100/query?platform=SLEEPER&queryType=TRANSACTIONS#2024"
    Then the API responds with status 200
    And the query response has 2 row(s)

  Scenario: An upstream auth failure records a FAILED job and writes no METADATA
    When the onboarder fails to reach the platform
    Then the onboarder returns status 502
    And a JOB_STATUS "FAILED" exists for the job
    And the JOB_STATUS failure_code is "ESPN_AUTH"
    And no METADATA item exists for the onboarded league
