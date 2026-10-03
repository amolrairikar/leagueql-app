Feature: View My Leagues on the landing page (frontend/landing-page / backend/user-leagues)
  A signed-in user can expand a list of every league they own, joined by invite, or
  opened on Sleeper, and open one without re-entering its league ID.

  Scenario: The button is hidden when signed out
    Given I am signed out
    When I open the landing page
    Then there is no "View My Leagues" button

  Scenario: Expanding and collapsing the panel
    Given I have leagues
    When I open the landing page
    And I click "View My Leagues"
    Then the "View My Leagues" button is expanded
    And I see the league "The Dynasty Bowl"
    When I click "View My Leagues"
    Then the "View My Leagues" button is collapsed
    And I do not see the league "The Dynasty Bowl"

  Scenario: Leagues are listed in API order with their details
    Given I have leagues
    When I open the landing page
    And I click "View My Leagues"
    Then the leagues are listed in order "The Dynasty Bowl, Office League, Fam Fantasy"
    And the league "The Dynasty Bowl" shows "Sleeper • 2019–2025 · 7 seasons"
    And the league "Fam Fantasy" shows "Moved from ESPN"
    And the league "Office League" shows a "Reconnect ESPN" flag
    And the league "The Dynasty Bowl" has no "Reconnect ESPN" flag
    And the "View My Leagues" button shows a count of 3
    And I see the hint "Missing a league? For ESPN or Yahoo, ask the league owner for an invite link."

  Scenario: A loading skeleton shows while the list is requested
    Given my leagues request is still in flight
    When I open the landing page
    And I click "View My Leagues"
    Then I see the leagues loading skeleton

  Scenario: An empty list offers to connect a league
    Given I have no leagues
    When I open the landing page
    And I click "View My Leagues"
    Then I see "No leagues yet"
    When I click the empty state's "Connect Your League"
    Then the connect form is shown
    And the "View My Leagues" button is collapsed

  Scenario: A server error is shown inline and can be retried
    Given my leagues request fails with status 500
    When I open the landing page
    And I click "View My Leagues"
    Then I see the error "Couldn't load your leagues. Check your connection and try again."
    Given I have leagues
    When I click "Try again"
    Then I see the league "The Dynasty Bowl"

  Scenario: A client error shows the API's message
    Given my leagues request fails with status 403
    When I open the landing page
    And I click "View My Leagues"
    Then I see the error "Not allowed"

  Scenario: Opening a league stores it and goes home
    Given I have leagues
    And opening a league succeeds
    When I open the landing page
    And I click "View My Leagues"
    And I click the league "Office League"
    Then I land on the league home page
    And the selected league is "555" on "ESPN" with seasons "2017,2018"

  Scenario: A failure opening a league is shown inline
    Given I have leagues
    And opening a league fails with status 403
    When I open the landing page
    And I click "View My Leagues"
    And I click the league "Office League"
    Then I see the error "Not a member of this league"
    And I am still on the landing page

  Scenario: The panel and the connect form are mutually exclusive
    Given I have leagues
    When I open the landing page
    And I click "View My Leagues"
    And I click the hero "Connect Your League"
    Then the connect form is shown
    And the "View My Leagues" button is collapsed
    When I click "View My Leagues"
    Then the connect form is not shown
    And the "View My Leagues" button is expanded
