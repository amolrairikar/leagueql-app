Feature: Demo mode (FE-015)
  In demo mode the app renders analytics from local fixtures and makes no live
  backend calls.

  Scenario: The dashboard renders from fixtures without any network call
    Given demo mode is active
    When I open the home dashboard in demo mode
    Then I see the headline stat "Total matchups"

  Scenario: The Sleeper-only Transactions page renders demo fixtures
    Given demo mode is active
    When I open the transactions page in demo mode
    Then I see a transaction card for the 2025 demo season

  Scenario: Returning to the landing page exits demo mode
    Given demo mode is active
    When I open the landing page
    Then demo mode is no longer active
