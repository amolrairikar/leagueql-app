Feature: Weekly awards & superlatives (frontend/weekly-awards)
  The matchups page hosts a free weekly-awards section: per-week award cards (highest
  and lowest score, biggest blowout, narrowest win, best loss, worst win) plus a week-to-date
  tally of how many each manager has collected.

  Scenario: Awards render for a week with games
    Given a season of matchups is available
    When I open the weekly awards
    Then I see the award "Highest Score"
    And I see the manager "Alice"
    And I see the tally heading "Manager"

  Scenario: A season without matchup data shows an empty state
    Given the season has no matchups
    When I open the weekly awards
    Then I see "Not enough matchup data for awards this season."

  Scenario: A failed load surfaces an inline message
    Given the matchup data fails to load
    When I open the weekly awards
    Then I see "Failed to load weekly awards."
