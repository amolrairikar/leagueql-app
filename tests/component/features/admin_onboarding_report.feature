Feature: Nightly admin onboarding report (backend/admin-onboarding-report)
  The scheduled Lambda queries the GSI3 all-leagues index and posts one Discord embed
  summarizing total leagues onboarded, active leagues (14d), the ESPN/SLEEPER split, and
  new onboards in the last 24h / 7d / 30d.

  Scenario: Digest reports aggregated onboarding health
    Given an onboarded league "canon-a" platform "SLEEPER" onboarded 0 days ago, last accessed 1 days ago
    And an onboarded league "canon-b" platform "ESPN" onboarded 3 days ago, last accessed 2 days ago
    And an onboarded league "canon-c" migrated to "SLEEPER" onboarded 20 days ago, never accessed
    When the nightly onboarding report runs
    Then the report field "Total onboarded" is "3"
    And the report field "Active (14d)" is "2"
    And the report field "ESPN / SLEEPER" is "1 / 2"
    And the report "New onboards" field contains "Last 24h: **1**"
    And the report "New onboards" field contains "Last 7d: **2**"
    And the report "New onboards" field contains "Last 30d: **3**"

  Scenario: Digest posts zeroes when no leagues are onboarded
    When the nightly onboarding report runs
    Then the report field "Total onboarded" is "0"
    And the report field "Active (14d)" is "0"
    And the report field "ESPN / SLEEPER" is "0 / 0"
