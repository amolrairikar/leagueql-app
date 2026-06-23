Feature: Weekly score distribution (FE-033)
  The premium Analytics page renders a per-manager box-and-whisker chart of weekly
  scores for the selected season, computed client-side from the MATCHUPS view and
  gated behind the premium_feature flag.

  Scenario: The chart renders for a season with regular-season games
    Given a season of regular-season matchups is available
    When I open the score distribution
    Then I see the manager "Alice"
    And I see the manager "Bob"

  Scenario: Hovering a manager's row reveals their numbers
    Given a season of regular-season matchups is available
    When I open the score distribution
    And I hover over the manager "Alice"
    Then I see the tooltip stat "Median"
    And I see the tooltip stat "IQR"

  Scenario: A season without regular-season data shows an empty state
    Given the season has no regular-season matchups
    When I open the score distribution
    Then I see "No regular-season scores to chart for this season yet."

  Scenario: A failed load surfaces an inline message
    Given the matchup data fails to load
    When I open the score distribution
    Then I see "Failed to load score-distribution data."

  Scenario: An expired subscription shows the locked overlay without fetching data
    Given the premium_feature flag is on and the league subscription has expired
    When I open the gated score distribution
    Then I see the paywall heading "Analytics is a premium feature"
    And the score distribution chart is not rendered
