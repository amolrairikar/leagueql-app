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

  Scenario: Each matchup preview card scrolls horizontally on its own
    Given an in-progress season with a played week 1 and a live week 2
    When I open the matchups page
    And I open the live-week matchup
    Then each preview card is its own horizontally scrollable container
    And the recent form usernames can wrap to fit the card
    And the close button sits outside every scrollable card

  Scenario: Top scorers stack by team on mobile
    Given an in-progress season with a played week 1 and a live week 2
    When I open the matchups page
    And I open the live-week matchup
    Then the top scorers are a single column on mobile and two columns from the sm breakpoint
    And "Alice"'s top scorers are listed above "Bob"'s

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

  Scenario: A Yahoo season with pending player scores shows a box score placeholder (frontend/lineup-data-status)
    Given a Yahoo season whose player scores are still loading
    When I open the Yahoo matchups page
    And I open the week 1 matchup
    Then I see the box score placeholder "Player scores still loading"
    And I see the team score "120.00"
    But I do not see the player "Pat Quarterback"

  Scenario: A Yahoo season with backfilled player scores shows the lineups (frontend/lineup-data-status)
    Given a Yahoo season whose player scores are loaded
    When I open the Yahoo matchups page
    And I open the week 1 matchup
    Then I see the player "Pat Quarterback"
    But I do not see the box score placeholder "Player scores still loading"

  Scenario: A Yahoo season with pending player scores notes the missing top scorers (frontend/lineup-data-status)
    Given a Yahoo season whose player scores are still loading
    When I open the Yahoo matchups page
    And I open the live-week matchup
    Then I see the note "Player scores for 2024 are still loading"
