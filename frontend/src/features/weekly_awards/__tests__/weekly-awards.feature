Feature: Weekly awards & superlatives (FE-032)
  The matchups page hosts a premium weekly-awards section: per-week award cards (highest
  and lowest score, biggest blowout, narrowest win, best loss, worst win) plus a week-to-date
  tally of how many each manager has collected. It is gated behind the premium_feature flag.

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

  Scenario: An expired subscription shows the locked overlay without fetching data
    Given the premium_feature flag is on and the league subscription has expired
    When I open the gated weekly awards
    Then I see the paywall heading "Weekly awards & superlatives is a premium feature"
    And the weekly awards are not rendered
