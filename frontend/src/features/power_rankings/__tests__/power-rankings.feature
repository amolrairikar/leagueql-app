Feature: Power rankings (frontend/power-rankings)
  The power rankings page ranks every team from the season's matchups, lets the user
  step through weeks, expands a team to show what drives its score, and shows inline
  empty and error states.

  Scenario: Rankings render for the latest week
    Given a season with three played weeks
    When I open the power rankings page
    Then the week picker shows "Week 4"
    And the teams are ranked "Team Amy", "Team Cal", "Team Ben", "Team Dee"
    And the formula section "How power rankings are calculated" is collapsed

  Scenario: Expanding the formula section
    Given a season with three played weeks
    When I open the power rankings page
    And I expand the formula section "How power rankings are calculated"
    Then I see the weights "Record", "Points scored", "Recent form", "Lineup efficiency"
    And I see the scaling example "How scaling works" with a scaled score of "68.8"

  Scenario: Collapsing the formula section
    Given a season with three played weeks
    When I open the power rankings page
    And I expand the formula section "How power rankings are calculated"
    And I collapse the formula section "How power rankings are calculated"
    Then I do not see "Points scored"

  Scenario: Stepping back to an earlier week
    Given a season with three played weeks
    When I open the power rankings page
    And I step to the previous week
    Then the week picker shows "Week 3"
    And Amy's record is "2-0"

  Scenario: The earliest week cannot be stepped back from
    Given a season with three played weeks
    When I open the power rankings page
    And I step to the previous week twice
    Then the week picker shows "Week 2"
    And the previous week button is disabled

  Scenario: Expanding a team shows its breakdown
    Given a season with three played weeks
    When I open the power rankings page
    And I expand "Team Amy"
    Then I see "What drives this score"
    And I see "Expected record"

  Scenario: Collapsing a team hides its breakdown
    Given a season with three played weeks
    When I open the power rankings page
    And I expand "Team Amy"
    And I collapse "Team Amy"
    Then I do not see "What drives this score"

  Scenario: Unplayed and playoff games are ignored
    Given a season with an unplayed week and a playoff game
    When I open the power rankings page
    Then the week picker shows "Week 4"
    And the teams are ranked "Team Amy", "Team Cal", "Team Ben", "Team Dee"

  Scenario: A season with no played games shows an empty message
    Given a season with no played games
    When I open the power rankings page
    Then I see "Power rankings will appear once games have been played this season."

  Scenario: A failed load surfaces an inline error
    Given the matchups fail to load
    When I open the power rankings page
    Then I see "Failed to load power rankings."
