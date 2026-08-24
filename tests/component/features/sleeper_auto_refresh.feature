Feature: Scheduled Sleeper auto-refresh (backend/scheduled-sleeper-auto-refresh)
  During the NFL season the Lambda invokes the onboarder in REFRESH mode for every
  onboarded Sleeper league; ESPN leagues are excluded and offseason/week-1 are skipped.

  Scenario: In-season run invokes the onboarder for each Sleeper league only
    Given an onboarded Sleeper league "100" canonical "canon-1"
    And an onboarded Sleeper league "200" canonical "canon-2"
    And an onboarded ESPN league "300" canonical "canon-3"
    When the auto-refresh runs with NFL state season_type "regular" week "10"
    Then the auto-refresh response status is "succeeded"
    And the onboarder was invoked 2 time(s)
    And the onboarder was invoked for league "100"
    And the onboarder was invoked for league "200"

  Scenario: Offseason runs are skipped
    Given an onboarded Sleeper league "100" canonical "canon-1"
    When the auto-refresh runs with NFL state season_type "off" week "5"
    Then the auto-refresh response status is "skipped"
    And the onboarder was invoked 0 time(s)

  Scenario: Week 1 is skipped (matchups not settled)
    Given an onboarded Sleeper league "100" canonical "canon-1"
    When the auto-refresh runs with NFL state season_type "regular" week "1"
    Then the auto-refresh response status is "skipped"
    And the onboarder was invoked 0 time(s)
