Feature: Authentication and protected routes (FE-019)
  Protected analytics routes require a signed-in user, except in demo mode where
  the guard is bypassed.

  Scenario: A signed-out user is redirected away from a protected route
    Given the user is signed out
    When the app opens a protected route
    Then I see "Connect Your League"

  Scenario: Demo mode bypasses authentication
    Given the user is signed out but demo mode is active
    When the app opens a protected route
    Then I see the demo banner
