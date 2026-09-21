Feature: Yahoo members proxy API (backend/yahoo-members-proxy)
  POST /leagues/{id}/yahoo_members fetches a Yahoo league's managers server-side using the
  caller's linked OAuth token, for the migration manager-mapping exercise. It is owner-gated.

  Background:
    Given a LEAGUE_LOOKUP exists for league "100" platform "SLEEPER" canonical "canon-1"

  Scenario: Managers are returned for a linked owner
    When I POST to yahoo_members for league "100" targeting Yahoo league "456" with a linked account
    Then the API responds with status 200
    And the query response has 1 row(s)

  Scenario: An unlinked account gets a reconnect signal
    When I POST to yahoo_members for league "100" targeting Yahoo league "456" without a link
    Then the API responds with status 403

  Scenario: A Yahoo league not in the caller's account is 404
    When I POST to yahoo_members for league "100" targeting Yahoo league "456" not in the account
    Then the API responds with status 404
