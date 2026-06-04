Feature: Query precomputed views API (BE-005)
  GET /leagues/{id}/query serves precomputed views, with collection queries
  concatenated and suffixed queries returning a single item.

  Background:
    Given a LEAGUE_LOOKUP exists for league "100" platform "SLEEPER" canonical "canon-1"

  Scenario: A collection query returns concatenated rows
    Given league "canon-1" has a "MATCHUPS#2024#WEEK#01" view with 3 row(s)
    When I GET "/leagues/100/query?platform=SLEEPER&queryType=MATCHUPS"
    Then the API responds with status 200
    And the query response has 3 row(s)
    And the response has Cache-Control "private, max-age=300"

  Scenario: A suffixed query returns a single item's data
    Given league "canon-1" has a "STANDINGS#2024" view with 2 row(s)
    When I GET "/leagues/100/query?platform=SLEEPER&queryType=SEASON_STANDINGS#2024"
    Then the API responds with status 200
    And the query response has 2 row(s)

  Scenario: An unrecognized queryType is rejected
    When I GET "/leagues/100/query?platform=SLEEPER&queryType=BOGUS"
    Then the API responds with status 400

  Scenario: A valid query with no stored data returns 404
    When I GET "/leagues/100/query?platform=SLEEPER&queryType=DRAFT#2024"
    Then the API responds with status 404

  Scenario: An expired subscription is gated with 402
    Given league "canon-1" has subscription_end_time "2000-01-01T00:00:00+00:00"
    And league "canon-1" has a "MATCHUPS#2024#WEEK#01" view with 1 row(s)
    When I GET "/leagues/100/query?platform=SLEEPER&queryType=MATCHUPS"
    Then the API responds with status 402
