Feature: Demo mode (FE-015)
  In demo mode the app renders analytics from local fixtures and makes no live
  backend calls.

  Scenario: The dashboard renders from fixtures without any network call
    Given demo mode is active
    When I open the home dashboard in demo mode
    Then I see the headline stat "Total matchups"
