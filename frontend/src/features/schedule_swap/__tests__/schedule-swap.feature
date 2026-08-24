Feature: Schedule-swap simulator (frontend/schedule-swap-simulator)
  The standings page hosts a free N×N schedule-swap matrix: each row is a team's
  weekly scores, each column a manager's schedule, and the diagonal is the actual record.

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
