Feature: ESPN members proxy API (BE-009)
  POST /leagues/{id}/espn_members proxies the ESPN Fantasy API server-side and maps
  members, falling back to the owner id when a display name is absent.

  Background:
    Given a LEAGUE_LOOKUP exists for league "100" platform "SLEEPER" canonical "canon-1"

  Scenario: Members are returned with a display-name fallback
    When I POST to espn_members for league "100" with ESPN returning 200
    Then the API responds with status 200
    And the query response has 2 row(s)

  Scenario: An upstream ESPN error surfaces as 502
    When I POST to espn_members for league "100" with ESPN returning 401
    Then the API responds with status 502
