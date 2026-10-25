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
    And I do not see "ESPN leagues are private and require logging in to ESPN to view. The SWID and ESPN S2 cookies provide the authentication required to fetch data. These cookies are not stored. To find your ESPN cookies:"

  Scenario: Expanding a landing page FAQ question reveals its answer
    When I open the landing page
    And I expand the FAQ question "Why do I need to provide my ESPN cookies?"
    Then I see "Private ESPN leagues require logging in to ESPN to view. The SWID and ESPN S2 cookies provide the authentication required to fetch data. These cookies are not stored unless you opt into automatic weekly refresh, in which case they are stored encrypted so LeagueQL can refresh your league for you. One set of stored cookies is shared by all of your ESPN leagues and is removed once none of them has automatic refresh on. To find your ESPN cookies:"
    And I see "Find SWID and espn_s2 and copy their values"
    And I see text containing "Autofill cookies from ESPN"

  Scenario: The landing page FAQ states the manual refresh limit
    When I open the landing page
    And I expand the FAQ question "My data looks outdated. How do I refresh it?"
    Then I see text containing "once per week per league"
    And I do not see text containing "manually anytime"

  Scenario: The Works with strip marks Yahoo as Beta
    When I open the landing page
    Then I see "Works with"
    And I see "Yahoo"
    And I see "Beta"

  Scenario: The Works with strip links to the feature request board
    When I open the landing page
    Then the "request" link points to "https://leagueql.supahub.com/en"

  Scenario: The Yahoo Beta badge explains how to report import issues
    When I open the landing page
    And I hover the Yahoo "Beta" badge
    Then a tooltip asks me to email support@leagueql.com with my league ID

  Scenario: The docs page renders
    When I open the docs page
    Then I see "Refresh League (ESPN only)"
    And I see "Turn Off Auto-Refresh (ESPN only)"

  Scenario: The docs page documents connecting a Yahoo league
    When I open the docs page
    Then I see "Yahoo redirects you back to LeagueQL, where onboarding resumes automatically. You will see the same progress bar as a Sleeper connect while we pull your league history, then land on your dashboard."

  Scenario: The docs page says Yahoo leagues refresh automatically
    When I open the docs page
    Then I see "Yahoo leagues refresh automatically each week during the season using your connected Yahoo account."
    And I do not see "Yahoo auto-refresh is opt-in"

  Scenario: The privacy policy discloses Yahoo OAuth token storage
    When I open the privacy page
    Then I see "Yahoo OAuth Tokens (for Yahoo leagues):"

  Scenario: The privacy policy discloses diagnostics, account data, and how deletion works
    When I open the privacy page
    Then I see "Better Stack:"
    And I see "Usage & Diagnostics:"
    And I see "The team you claim as yours on the My Team page"
    And I see text containing "stored Yahoo tokens are removed when you delete your last Yahoo league"
    And I see text containing "Request any other removal"

  Scenario: The extension privacy policy names the real autofill button
    When I open the extension privacy page
    Then I see text containing "Autofill cookies from ESPN"
    And I do not see text containing "Autofill from ESPN"

  Scenario: The docs page documents ESPN refresh limits and shared cookie removal
    When I open the docs page
    Then I see text containing "Each league can be refreshed manually at most once per week."
    And I see text containing "removed once none of them has automatic refresh on"

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
