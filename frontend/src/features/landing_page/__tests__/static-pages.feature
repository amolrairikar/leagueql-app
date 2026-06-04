Feature: Public pages render (FE-001, FE-016, FE-017, FE-018)
  The public marketing and policy pages render without a connected league.

  Scenario: The landing page renders its primary call to action
    When I open the landing page
    Then I see "Connect Your League"

  Scenario: The docs page renders
    When I open the docs page
    Then I see "Refresh League"

  Scenario: The changelog page renders
    When I open the changelog page
    Then I see the heading "Changelog"

  Scenario: The privacy policy page renders
    When I open the privacy page
    Then I see the heading "Privacy Policy"
