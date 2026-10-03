Feature: Yahoo attribution footer (frontend/yahoo-attribution)
  In-app pages for a Yahoo league end with the Yahoo Fantasy attribution required by Yahoo's
  API terms. It never appears for ESPN or Sleeper leagues, or in demo mode.

  Scenario: Yahoo league shows the attribution
    Given I am viewing a Yahoo league
    When I render the attribution footer
    Then I see the Yahoo Fantasy logo and attribution text linking to Yahoo Fantasy

  Scenario: ESPN league shows no attribution
    Given I am viewing an ESPN league
    When I render the attribution footer
    Then I do not see the Yahoo attribution

  Scenario: Sleeper league shows no attribution
    Given I am viewing a Sleeper league
    When I render the attribution footer
    Then I do not see the Yahoo attribution

  Scenario: Demo mode shows no attribution
    Given I am viewing the demo league
    When I render the attribution footer
    Then I do not see the Yahoo attribution
