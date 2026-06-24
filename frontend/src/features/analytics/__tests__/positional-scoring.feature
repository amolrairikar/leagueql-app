Feature: Positional scoring breakdown (FE-036)
  The premium Analytics page renders a stacked bar chart of each manager's season
  starter points split by position, computed client-side from the MATCHUPS view and
  gated behind the premium_feature flag.

  Scenario: The chart renders a legend of the positions present
    Given a season of matchups with starter stats is available
    When I open the positional scoring
    Then I see the position "QB"
    And I see the position "RB"

  Scenario: A season without matchup data shows an empty state
    Given the season has no matchups
    When I open the positional scoring
    Then I see "No starter scoring to chart for this season yet."

  Scenario: A failed load surfaces an inline message
    Given the matchup data fails to load
    When I open the positional scoring
    Then I see "Failed to load positional-scoring data."

  Scenario: An expired subscription shows the locked overlay without fetching data
    Given the premium_feature flag is on and the league subscription has expired
    When I open the gated positional scoring
    Then I see the paywall heading "Analytics is a premium feature"
    And the positional scoring chart is not rendered
