Feature: In-dashboard ESPN refresh dialog (frontend/navigation-sidebar / frontend/connect-league)
  The Refresh League action opens a dialog where an ESPN league owner enters their
  SWID/espn_s2 cookies and the league refreshes in place. The season is derived
  automatically, so no season is entered.

  Scenario: Refreshing with cookies pulls the latest data in place
    Given refreshing my ESPN league will complete successfully and the current season is "2026"
    When I enter my ESPN cookies and refresh from the dialog
    Then the refresh request carried season "2026"
    And the refresh request did not opt into auto-refresh
    And the dashboard reloads with the fresh data

  Scenario: Enabling auto-refresh in the dialog sends the opt-in
    Given refreshing my ESPN league will complete successfully and the current season is "2026"
    When I enter my ESPN cookies, enable auto-refresh, and refresh from the dialog
    Then the refresh request opted into auto-refresh
    And the dashboard reloads with the fresh data

  Scenario: A refresh blocked by the weekly cooldown shows a benign notice
    Given refreshing my ESPN league is blocked by the weekly cooldown with message "This league can only be refreshed once per week."
    When I enter my ESPN cookies and refresh from the dialog
    Then I see the notice title "Refresh not available yet"
    And the dashboard does not reload

  Scenario: Refreshing without cookies shows an inline error
    Given I open the refresh dialog for my ESPN league
    When I refresh from the dialog without entering cookies
    Then I see an inline error "Enter your SWID and espn_s2"
    And no refresh request was made
