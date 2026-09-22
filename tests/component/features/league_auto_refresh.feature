Feature: Scheduled league auto-refresh (backend/scheduled-league-auto-refresh)
  During the NFL season the Lambda invokes the onboarder in REFRESH mode for every onboarded
  Sleeper league, and for Yahoo and ESPN leagues that have opted into auto-refresh. Yahoo and ESPN
  are dispatched with their resolved owner (ESPN also with the current season and no cookies);
  leagues not opted in, offseason, and week 1 are skipped.

  Scenario: In-season run invokes the onboarder for each Sleeper league only
    Given an onboarded Sleeper league "100" canonical "canon-1" season "2024"
    And an onboarded Sleeper league "200" canonical "canon-2" season "2024"
    And an onboarded ESPN league "300" canonical "canon-3"
    When the auto-refresh runs with NFL state season_type "regular" week "10"
    Then the auto-refresh response status is "succeeded"
    And the onboarder was invoked 2 time(s)
    And the onboarder was invoked for league "100"
    And the onboarder was invoked for league "200"

  Scenario: In-season run refreshes an opted-in Yahoo league with its resolved owner
    Given an onboarded Sleeper league "100" canonical "canon-1" season "2024"
    And an onboarded Yahoo league "400" canonical "canon-4" season "2024" owner "user-42"
    When the auto-refresh runs with NFL state season_type "regular" week "10"
    Then the auto-refresh response status is "succeeded"
    And the onboarder was invoked 2 time(s)
    And the onboarder was invoked for league "100"
    And the onboarder was invoked for Yahoo league "400" with owner "user-42"

  Scenario: In-season run refreshes an opted-in ESPN league with owner, season, and no cookies
    Given an onboarded Sleeper league "100" canonical "canon-1" season "2024"
    And an auto-refresh ESPN league "600" canonical "canon-6" season "2024" owner "user-7"
    When the auto-refresh runs with NFL state season_type "regular" week "10"
    Then the auto-refresh response status is "succeeded"
    And the onboarder was invoked 2 time(s)
    And the onboarder was invoked for ESPN league "600" with owner "user-7" and season "2024"

  Scenario: A Yahoo league not opted into auto-refresh is skipped
    Given a not-opted-in Yahoo league "700" canonical "canon-7" season "2024" owner "user-9"
    When the auto-refresh runs with NFL state season_type "regular" week "10"
    Then the auto-refresh response status is "succeeded"
    And the onboarder was invoked 0 time(s)

  Scenario: An opted-in Yahoo league with no owner is skipped
    Given an onboarded Yahoo league "500" canonical "canon-5" season "2024" with no owner
    When the auto-refresh runs with NFL state season_type "regular" week "10"
    Then the auto-refresh response status is "succeeded"
    And the onboarder was invoked 0 time(s)

  Scenario: Offseason runs are skipped
    Given an onboarded Sleeper league "100" canonical "canon-1" season "2024"
    When the auto-refresh runs with NFL state season_type "off" week "5"
    Then the auto-refresh response status is "skipped"
    And the onboarder was invoked 0 time(s)

  Scenario: Week 1 is skipped (matchups not settled)
    Given an onboarded Sleeper league "100" canonical "canon-1" season "2024"
    When the auto-refresh runs with NFL state season_type "regular" week "1"
    Then the auto-refresh response status is "skipped"
    And the onboarder was invoked 0 time(s)

  Scenario: Leagues behind the current NFL season are skipped
    Given an onboarded Sleeper league "100" canonical "canon-1" season "2024"
    And a pending Sleeper renewal "150" canonical "canon-1" pending season "2024"
    And an onboarded Sleeper league "200" canonical "canon-2" season "2025"
    When the auto-refresh runs with NFL state season_type "regular" week "10" season "2025"
    Then the auto-refresh response status is "succeeded"
    And the onboarder was invoked 1 time(s)
    And the onboarder was invoked for league "200"
