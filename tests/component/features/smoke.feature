Feature: Component harness smoke test
  Confirms the moto-backed harness loads every component (onboarder, processor,
  sleeper_refresh, API) and that AWS calls hit the in-memory moto stack rather
  than a real account.

  Scenario: The API health check responds
    When I GET "/health"
    Then the API responds with status 200
    And the API response detail is "Healthy!"

  Scenario: The moto DynamoDB table is reachable
    Given a LEAGUE_LOOKUP exists for league "111" platform "SLEEPER" canonical "canon-1"
    When I GET "/leagues/111?platform=SLEEPER"
    Then the API responds with status 200
