Feature: Sleeper stale-season banner (frontend/sleeper-stale-season-banner)
  A Sleeper league owner is told to onboard the current season's league ID when the current
  fantasy season is after the league's latest onboarded season. No banner appears for ESPN
  leagues, non-owners, in demo mode, or when the league is up to date.

  Scenario: Stale-season Sleeper league shows the banner to the owner
    Given the date is September 2026
    And I am the owner of a Sleeper league whose latest onboarded season is 2025
    When I render the stale-season banner
    Then I see the stale-season banner with a link to the landing page

  Scenario: Up-to-date Sleeper league shows no banner
    Given the date is September 2026
    And I am the owner of a Sleeper league whose latest onboarded season is 2026
    When I render the stale-season banner
    Then I do not see the stale-season banner

  Scenario: Before September the season has not yet flipped
    Given the date is August 2026
    And I am the owner of a Sleeper league whose latest onboarded season is 2025
    When I render the stale-season banner
    Then I do not see the stale-season banner

  Scenario: In September the season flips and the banner appears
    Given the date is September 2026
    And I am the owner of a Sleeper league whose latest onboarded season is 2025
    When I render the stale-season banner
    Then I see the stale-season banner with a link to the landing page

  Scenario: A non-owner of a stale-season Sleeper league sees no banner
    Given the date is September 2026
    And I am a non-owner of a Sleeper league whose latest onboarded season is 2025
    When I render the stale-season banner
    Then I do not see the stale-season banner

  Scenario: ESPN league never shows the banner
    Given the date is September 2026
    And I am the owner of an ESPN league whose latest onboarded season is 2024
    When I render the stale-season banner
    Then I do not see the stale-season banner

  Scenario: Demo mode never shows the banner
    Given the date is September 2026
    And I am viewing a stale-season Sleeper league in demo mode
    When I render the stale-season banner
    Then I do not see the stale-season banner

  Scenario: A league with no onboarded seasons shows no banner
    Given the date is September 2026
    And I am the owner of a Sleeper league with no onboarded seasons
    When I render the stale-season banner
    Then I do not see the stale-season banner
