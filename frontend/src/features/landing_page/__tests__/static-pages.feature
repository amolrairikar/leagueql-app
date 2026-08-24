Feature: Public pages render (frontend/landing-page, frontend/instructions-docs, frontend/privacy-pages, frontend/changelog)
  The public marketing and policy pages render without a connected league.

  Scenario: The landing page renders its primary call to action
    When I open the landing page
    Then I see "Connect Your League"

  Scenario: The landing page showcases the product and feature highlights
    When I open the landing page
    Then I see "See it in action"
    And I see "Complete History"

  Scenario: The landing page still renders when the league count endpoint fails
    When I open the landing page with the counts endpoint unavailable
    Then I see "Connect Your League"

  Scenario: The docs page renders
    When I open the docs page
    Then I see "Refresh League"

  Scenario: The privacy policy page renders
    When I open the privacy page
    Then I see the heading "Privacy Policy"

  Scenario: The changelog page renders
    When I open the changelog page
    Then I see the heading "Changelog"
    And I see "v1.1.0"
