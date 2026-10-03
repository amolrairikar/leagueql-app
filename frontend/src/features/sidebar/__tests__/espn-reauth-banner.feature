Feature: ESPN re-auth banner (frontend/refresh-reminder-banner)
  When ESPN rejects the saved cookies of an auto-refreshed ESPN league, its owner
  is told that automatic refresh is paused and pointed at the sidebar's Update
  ESPN Cookies action. Nobody else sees it, and it disappears once the cookies
  are re-entered.

  Scenario: The owner sees the banner when their saved cookies were rejected
    Given I own an ESPN league whose saved cookies ESPN rejected
    When I render the ESPN re-auth banner
    Then I see the re-auth banner with no dismiss control

  Scenario: Healthy cookies show no banner
    Given I own an auto-refreshed ESPN league whose saved cookies still work
    When I render the ESPN re-auth banner
    Then I do not see the re-auth banner

  Scenario: A non-owner sees no banner
    Given I am a non-owner of an ESPN league
    When I render the ESPN re-auth banner
    Then I do not see the re-auth banner

  Scenario: A Sleeper league never shows the banner
    Given I own a Sleeper league whose metadata reports re-auth required
    When I render the ESPN re-auth banner
    Then I do not see the re-auth banner

  Scenario: Demo mode never shows the banner
    Given I am viewing an ESPN league with rejected cookies in demo mode
    When I render the ESPN re-auth banner
    Then I do not see the re-auth banner
