Feature: Power rankings trend (FE-033)
  The Analytics page renders a multi-line power-rankings trend chart for the
  selected season, computed client-side from the MATCHUPS view.

  Scenario: The chart renders a line per manager for a season
    Given a season of regular-season matchups is available
    When I open the power rankings
    Then I see the manager "Alice"
    And I see the manager "Bob"

  Scenario: A season without enough data shows an empty state
    Given the season has no regular-season matchups
    When I open the power rankings
    Then I see "Not enough regular-season games to rank teams for this season yet."

  Scenario: A failed load surfaces an inline message
    Given the matchup data fails to load
    When I open the power rankings
    Then I see "Failed to load power-rankings data."
