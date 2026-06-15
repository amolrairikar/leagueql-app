Feature: Schedule-swap simulator (FE-031)
  The standings page hosts a premium N×N schedule-swap matrix: each row is a team's
  weekly scores, each column a manager's schedule, and the diagonal is the actual record.
  It is gated behind the premium_feature flag.

  Scenario: The matrix renders for a season with regular-season games
    Given a season of regular-season matchups is available
    When I open the schedule-swap simulator
    Then I see the manager "Alice"
    And I see the actual record "Actual 2-0"

  Scenario: A season without enough data shows an empty state
    Given the season has no regular-season matchups
    When I open the schedule-swap simulator
    Then I see "Not enough regular-season data to simulate schedule swaps for this season."

  Scenario: A failed load surfaces an inline message
    Given the matchup data fails to load
    When I open the schedule-swap simulator
    Then I see "Failed to load schedule-swap data."

  Scenario: An expired subscription shows the locked overlay without fetching data
    Given the premium_feature flag is on and the league subscription has expired
    When I open the gated schedule-swap simulator
    Then I see the paywall heading "Schedule-swap simulator is a premium feature"
    And the schedule-swap matrix is not rendered
