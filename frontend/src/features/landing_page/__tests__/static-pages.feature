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

  Scenario: The landing page FAQ starts collapsed
    When I open the landing page
    Then I see "Why do I need to provide my ESPN cookies?"
    And I do not see "ESPN leagues are private and require logging in to ESPN to view. The SWID and ESPN S2 cookies provide the authentication required to fetch data. These cookies are not stored."

  Scenario: Expanding a landing page FAQ question reveals its answer
    When I open the landing page
    And I expand the FAQ question "Why do I need to provide my ESPN cookies?"
    Then I see "ESPN leagues are private and require logging in to ESPN to view. The SWID and ESPN S2 cookies provide the authentication required to fetch data. These cookies are not stored."

  Scenario: The docs page renders
    When I open the docs page
    Then I see "Refresh League"

  Scenario: The docs page no longer shows the FAQ
    When I open the docs page
    Then I do not see "Why do I need to provide my ESPN cookies?"

  Scenario: The privacy policy page renders
    When I open the privacy page
    Then I see the heading "Privacy Policy"

  Scenario: The changelog page renders
    When I open the changelog page
    Then I see the heading "Changelog"
    And I see "v1.1.0"
