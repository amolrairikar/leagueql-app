Feature: Delete league API (backend/delete-league)
  DELETE /leagues/{id} sweeps all canonical-keyed items + S3 objects and
  decrements LEAGUE_COUNT.

  Background:
    Given the LEAGUE_COUNT starts at 5
    And a LEAGUE_LOOKUP exists for league "100" platform "SLEEPER" canonical "canon-1"
    And league "canon-1" has a "STANDINGS#2024" view with 2 row(s)
    And league "canon-1" has raw data stored in S3

  Scenario: Delete sweeps all data
    When I DELETE "/leagues/100?platform=SLEEPER"
    Then the API responds with status 200
    And the API response detail is "Successfully deleted league"
    And no DynamoDB items remain for league "canon-1"
    And the LEAGUE_COUNT is 4

  Scenario: An un-onboarded league returns 404
    When I DELETE "/leagues/404?platform=SLEEPER"
    Then the API responds with status 404
