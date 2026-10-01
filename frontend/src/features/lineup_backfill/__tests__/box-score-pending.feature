Feature: Box score pending state (frontend/lineup-data-status)
  Every feature's box score (matchups, matchup records, player records, manager
  history, manager comparison, playoff bracket) renders the shared box score card,
  which shows a placeholder and no lineup-efficiency chip for a season whose player
  scores are still loading.

  Scenario: A pending season shows the placeholder and no lineup efficiency
    Given a Yahoo league whose 2024 player scores are still loading
    When I render a 2024 box score
    Then I see 2 "Player scores still loading" placeholders
    And I see no lineup efficiency
    And I do not see the player "Pat Quarterback"

  Scenario: A loaded season shows lineups and lineup efficiency
    Given a Yahoo league whose 2024 player scores are loaded
    When I render a 2024 box score
    Then I see the player "Pat Quarterback"
    And I see lineup efficiency
