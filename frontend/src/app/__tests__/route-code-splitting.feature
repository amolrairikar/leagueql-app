Feature: Route code splitting (frontend/route-code-splitting)
  Each route's page code loads on demand, with a spinner while it loads and an
  error fallback if the load fails.

  Scenario: The landing page does not load league pages
    Given the user is signed out
    When the app opens the landing page
    Then the standings and home page code is not requested

  Scenario: An in-app page shows a spinner while keeping the app chrome
    Given the user is in demo mode
    And the home page code is still loading
    When the app opens the home page
    Then I see the loading spinner and the demo banner
    When the home page code finishes loading
    Then I see "Home page loaded"

  Scenario: A public page shows a spinner while loading
    Given the user is signed out
    And the docs page code is still loading
    When the app opens the docs page
    Then I see the loading spinner
    When the docs page code finishes loading
    Then I see "Docs page loaded"

  Scenario: A failed page load shows the error fallback
    Given the user is in demo mode
    And the standings page code fails to load
    When the app opens the standings page
    Then I see "Something went wrong"

  Scenario: Navigating away from a failed page recovers
    Given the user is in demo mode
    And the standings page code fails to load
    When the app opens the standings page
    And the user navigates to the home page
    Then I see "Home page loaded"
