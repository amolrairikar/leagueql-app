Feature: Delete league API (BE-007)
  DELETE /leagues/{id} cancels the Stripe subscription BEFORE removing data, sweeps
  all canonical-keyed items + S3 objects, decrements LEAGUE_COUNT, and leaves the
  durable TRIAL_USED marker intact.

  Background:
    Given the LEAGUE_COUNT starts at 5
    And a LEAGUE_LOOKUP exists for league "100" platform "SLEEPER" canonical "canon-1"
    And league "canon-1" has a "STANDINGS#2024" view with 2 row(s)
    And league "canon-1" has raw data stored in S3
    And a durable TRIAL_USED marker exists for league "100" platform "SLEEPER"

  Scenario: Delete sweeps all data but preserves the durable trial marker
    When I DELETE "/leagues/100?platform=SLEEPER"
    Then the API responds with status 200
    And the API response detail is "Successfully deleted league"
    And no DynamoDB items remain for league "canon-1"
    And the LEAGUE_COUNT is 4
    And a TRIAL_USED marker still exists for league "100" platform "SLEEPER"

  Scenario: An un-onboarded league returns 404
    When I DELETE "/leagues/404?platform=SLEEPER"
    Then the API responds with status 404

  Scenario: Subscription is canceled before any data is removed
    Given league "canon-1" records stripe subscription "sub_1"
    When I DELETE league "100" platform "SLEEPER" with Stripe cancel succeeding
    Then the API responds with status 200
    And the Stripe subscription was canceled
    And no DynamoDB items remain for league "canon-1"

  Scenario: A failed cancellation aborts the delete with data intact
    Given league "canon-1" records stripe subscription "sub_1"
    When I DELETE league "100" platform "SLEEPER" with Stripe cancel failing
    Then the API responds with status 500
    And a METADATA item still exists for league "canon-1"
