Feature: Yahoo OAuth linking (backend/yahoo-oauth)
  The API links a Yahoo account via the OAuth authorization-code flow: authorize mints a
  single-use state, the callback exchanges the code and stores an encrypted token item, and
  onboarding a Yahoo league is gated on a linked token. The Yahoo Fantasy data client is a
  later increment, so a linked onboard reports "coming soon".

  Scenario: Linking a Yahoo account and then onboarding shows coming soon
    When I start the Yahoo authorization for league "45.l.678"
    Then the API responds with status 200
    When Yahoo redirects back to the callback with a valid code
    Then the callback redirects with the linked marker
    And a YAHOO_OAUTH token item exists for the default user with encrypted tokens
    When I POST an ONBOARD of league "45.l.678" on "YAHOO"
    Then the API responds with status 200
    And the response data field "code" equals "YAHOO_COMING_SOON"

  Scenario: Callback with an unknown state does not link
    When Yahoo redirects back to the callback with code "abc" and state "never-issued"
    Then the callback redirects with the not-linked marker

  Scenario: Onboarding a Yahoo league without a linked account is rejected
    When I POST an ONBOARD of league "45.l.678" on "YAHOO"
    Then the API responds with status 403
    And the API response detail contains "Link your Yahoo account first"
