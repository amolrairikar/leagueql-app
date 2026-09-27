Feature: Matchups and box scores (frontend/matchups)
  The matchups page lists a season/week's matchups and surfaces an inline error
  when the data fails to load.

  Scenario: Matchups render when data loads
    Given matchup data is available
    When I open the matchups page
    Then I see the manager "Alice"

  Scenario: A failed load surfaces an inline error
    Given the matchup data fails to load
    When I open the matchups page
    Then I see "Failed to load matchups."

  Scenario: An in-progress season hides future weeks past the current week
    Given an in-progress season with played weeks 1-2 and unplayed weeks 3-4
    When I open the matchups page
    Then I see the week button "Wk 3"
    But I do not see the week button "Wk 4"

  Scenario: A live-week matchup opens the matchup preview
    Given an in-progress season with a played week 1 and a live week 2
    When I open the matchups page
    And I open the live-week matchup
    Then I see the matchup preview

  Scenario: A played matchup opens the box score
    Given an in-progress season with a played week 1 and a live week 2
    When I open the matchups page
    And I open the week 1 matchup
    Then I see the box score

  Scenario: The season's first week renders the preview without scores
    Given the first week of a season with no games played
    When I open the matchups page
    And I open the live-week matchup
    Then I see the matchup preview

  Scenario: Consistency is hidden early in the season
    Given an in-progress season with a played week 1 and a live week 2
    When I open the matchups page
    And I open the live-week matchup
    Then I do not see the head-to-head consistency stat

  Scenario: Consistency appears once each team's scoring differs
    Given an in-progress season with three played weeks and a live week 4
    When I open the matchups page
    And I open the live-week matchup
    Then I see the head-to-head consistency stat
