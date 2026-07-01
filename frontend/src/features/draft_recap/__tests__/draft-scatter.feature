Feature: Draft value scatter (FE-038)
  The premium Draft Recap scatterplot plots each scored pick's draft position against
  its season points, filterable by a single position dropdown, computed client-side
  from the DRAFT view and gated behind the premium_feature flag.

  Scenario: The scatter renders a legend of the positions present
    Given a season of scored draft picks is available
    When I open the draft value scatter
    Then I see the position "QB"
    And I see the position "RB"

  Scenario: Filtering to a position narrows the plot to that position
    Given a season of scored draft picks is available
    When I open the draft value scatter
    And I filter to the position "RB"
    Then I see the position "RB"
    And I do not see the position "QB"

  Scenario: A season with no scored picks shows an empty state
    Given the season has draft picks but none are scored
    When I open the draft value scatter
    Then I see "No scored draft picks to chart for this season yet."

  Scenario: A failed load surfaces an inline message
    Given the draft data fails to load
    When I open the draft value scatter
    Then I see "Failed to load draft data."

  Scenario: An expired subscription shows the locked overlay without fetching data
    Given the premium_feature flag is on and the league subscription has expired
    When I open the gated draft value scatter
    Then I see the paywall heading "Draft value is a premium feature"
    And the draft value scatter is not rendered
