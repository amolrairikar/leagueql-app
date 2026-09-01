Feature: Refresh reminder banner (frontend/refresh-reminder-banner)
  An ESPN league owner is reminded to refresh when the league's data is more than
  7 days old. No reminder appears for Sleeper leagues, non-owners, or in demo mode.

  Scenario: Stale ESPN league shows the reminder to the owner
    Given I am the owner of an ESPN league last refreshed 10 days ago
    When I render the refresh reminder banner
    Then I see the refresh reminder

  Scenario: Fresh ESPN league shows no reminder
    Given I am the owner of an ESPN league last refreshed 1 day ago
    When I render the refresh reminder banner
    Then I do not see the refresh reminder

  Scenario: Never-refreshed ESPN league falls back to onboarded date
    Given I am the owner of an ESPN league never refreshed but onboarded 10 days ago
    When I render the refresh reminder banner
    Then I see the refresh reminder

  Scenario: Recently onboarded ESPN league shows no reminder
    Given I am the owner of an ESPN league never refreshed but onboarded 1 day ago
    When I render the refresh reminder banner
    Then I do not see the refresh reminder

  Scenario: Sleeper league never shows the reminder
    Given I am the owner of a Sleeper league last refreshed 10 days ago
    When I render the refresh reminder banner
    Then I do not see the refresh reminder

  Scenario: A non-owner of a stale ESPN league sees no reminder
    Given I am a non-owner of an ESPN league last refreshed 10 days ago
    When I render the refresh reminder banner
    Then I do not see the refresh reminder

  Scenario: Demo mode never shows the reminder
    Given I am viewing a stale ESPN league in demo mode
    When I render the refresh reminder banner
    Then I do not see the refresh reminder
