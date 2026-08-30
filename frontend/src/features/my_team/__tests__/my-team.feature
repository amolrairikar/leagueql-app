Feature: My Team report card

  A personal report card filtered to one team the user picks, computed
  client-side from the season's precomputed views.

  Scenario: The report renders for a Sleeper team
    Given a Sleeper league with team data
    When I open my team
    Then I see "Autobots"
    And I see the section "Recent form"
    And I see the section "Draft report"
    And I see the section "Trade report"
    And I see the section "Insights"

  Scenario: Selecting a different team re-filters the report
    Given a Sleeper league with team data
    When I open my team
    And I select the team "Bob"
    Then I see "Decepticons"

  Scenario: ESPN leagues gate the trade report
    Given an ESPN league with team data
    When I open my team
    Then I see "Transactions are available on Sleeper leagues."

  Scenario: A failed load surfaces an inline message
    Given the team data fails to load
    When I open my team
    Then I see "Failed to load your team."

  Scenario: A season without data shows an empty state
    Given the season has no team data
    When I open my team
    Then I see "No team data for this season yet."
