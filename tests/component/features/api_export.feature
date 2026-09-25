Feature: Export league data API (backend/league-export)
  GET /leagues/{id}/export bundles the processed views for the selected seasons,
  keyed by season then view name, gated by league membership like the query endpoint.

  Background:
    Given a LEAGUE_LOOKUP exists for league "100" platform "SLEEPER" canonical "canon-1"

  Scenario: Export bundles views for the selected seasons
    Given league "canon-1" has a "STANDINGS#2024" view with 2 row(s)
    And league "canon-1" has a "MATCHUPS#2024#WEEK#01" view with 3 row(s)
    And league "canon-1" has a "TRANSACTIONS#2024#0000" view with 1 row(s)
    And league "canon-1" has a "STANDINGS#2023" view with 2 row(s)
    And league "canon-1" has team rows for seasons "2023,2024"
    When I GET "/leagues/100/export?platform=SLEEPER&seasons=2023,2024"
    Then the API responds with status 200
    And the response has Cache-Control "private, max-age=300"
    And the export response has season "2024"
    And the export response has season "2023"
    And the export season "2024" has view "standings" with 2 row(s)
    And the export season "2024" has view "matchups" with 3 row(s)
    And the export season "2024" has view "transactions" with 1 row(s)
    And the export season "2024" has view "teams" with 1 row(s)
    And the export season "2024" has no view "draft"
    And the export season "2023" has view "standings" with 2 row(s)
    And the export season "2023" has no view "matchups"

  Scenario: Export with no valid seasons is rejected
    When I GET "/leagues/100/export?platform=SLEEPER&seasons=1999"
    Then the API responds with status 400

  Scenario: Export with no stored data returns 404
    When I GET "/leagues/100/export?platform=SLEEPER&seasons=2024"
    Then the API responds with status 404
