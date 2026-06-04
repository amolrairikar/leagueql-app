Feature: Subscription access control (BE-014)
  Gated endpoints require a future subscription_end_time; ungated endpoints stay
  reachable regardless of subscription.

  Background:
    Given a LEAGUE_LOOKUP exists for league "100" platform "SLEEPER" canonical "canon-1"
    And league "canon-1" has a "MATCHUPS#2024#WEEK#01" view with 1 row(s)

  Scenario: A future subscription reaches a gated endpoint
    Given league "canon-1" has subscription_end_time "2999-01-01T00:00:00+00:00"
    When I GET "/leagues/100/query?platform=SLEEPER&queryType=MATCHUPS"
    Then the API responds with status 200

  Scenario: A past subscription is gated with 402
    Given league "canon-1" has subscription_end_time "2000-01-01T00:00:00+00:00"
    When I GET "/leagues/100/query?platform=SLEEPER&queryType=MATCHUPS"
    Then the API responds with status 402

  Scenario: An absent subscription is gated with 402
    Given league "canon-1" has no subscription_end_time
    When I GET "/leagues/100/query?platform=SLEEPER&queryType=MATCHUPS"
    Then the API responds with status 402

  Scenario: GET league metadata is never gated
    Given league "canon-1" has no subscription_end_time
    When I GET "/leagues/100?platform=SLEEPER"
    Then the API responds with status 200
