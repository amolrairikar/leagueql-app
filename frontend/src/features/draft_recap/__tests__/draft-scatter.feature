Feature: Draft value scatter (frontend/draft-value-scatter)
  The free Draft Recap scatterplot plots each scored pick's draft position against
  its season points, filterable by a single position dropdown, computed client-side
  from the DRAFT view.

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
