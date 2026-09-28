Feature: My Team nav entry (frontend/navigation-sidebar, frontend/my-team)
  The "My Team" entry is always shown, directly under Home and above Standings.

  Scenario: Entry placed under Home
    When I render the sidebar
    Then the nav items begin "Home, My Team, Standings"
    And the "My Team" nav item links to "/my_team"
