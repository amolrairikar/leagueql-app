Feature: Manager history (frontend/manager-history)
  The manager history page shows each manager's per-season records and rivalries,
  with an inline error when the data fails to load. Each season card expands in
  place to show that season's schedule.

  Scenario: Manager history renders when data loads
    Given manager history data is available
    When I open the manager history page
    Then I see the manager "Alice"

  Scenario: An unplayed 0-0 week never appears in a manager's season schedule
    Given manager history data includes an unplayed 0-0 week
    When I open the manager history page
    And I open the 2024 season schedule
    Then the schedule shows the played game but not the unplayed 0-0 game

  Scenario: Expanding a season shows its schedule inline
    Given manager history data is available
    When I open the manager history page
    And I open the 2024 season schedule
    Then the 2024 season is expanded with its schedule shown inline
    And no dialog is open

  Scenario: Clicking an expanded season again collapses it
    Given manager history data is available
    When I open the manager history page
    And I open the 2024 season schedule
    And I click the 2024 season again
    Then the 2024 season is collapsed and its schedule is hidden

  Scenario: Several seasons stay expanded
    Given manager history data for the 2023 and 2024 seasons
    When I open the manager history page for both seasons
    And I open the 2024 season schedule
    And I open the 2023 season schedule
    Then both the 2023 and 2024 seasons are expanded

  Scenario: Selecting a game shows its box score inside the season
    Given manager history data is available
    When I open the manager history page
    And I open the 2024 season schedule
    And I select the week 1 game
    Then the week 1 box score is shown inside the 2024 season

  Scenario: An in-progress season shows the current standings position, not rank 0
    Given manager history data for an in-progress season with final_rank 0
    When I open the manager history page
    Then the season card shows the current standings finish "1st" and never "0th"
    And the season card shows no playoff result pill

  Scenario: A finalized season keeps its playoff result pill
    Given manager history data is available
    When I open the manager history page
    Then the season card shows the "Champion" result pill

  Scenario: A failed load surfaces an inline error
    Given the manager history data fails to load
    When I open the manager history page
    Then I see "Failed to load manager data."

  Scenario: Runner-up of an early final
    Given manager history data where Alice lost a "Finals" game played in matchup period 15
    When I open the manager history page
    Then the season card shows the "Runner-up" result pill
    And the season card shows the finish "2nd"
