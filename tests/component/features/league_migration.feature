Feature: League migration API (BE-003)
  POST /leagues/{id}/migrate records the destination lookup + manager mapping and
  triggers the onboarder, preserving all-time history under one canonical league.

  Background:
    Given a LEAGUE_LOOKUP exists for league "100" platform "SLEEPER" canonical "canon-1"

  Scenario: Migration writes mapping records and triggers the onboarder
    When I POST a migration of league "100" from "SLEEPER" to "ESPN" league "777"
    Then the API responds with status 202
    And a PLATFORM_MIGRATION item exists for league "canon-1"
    And a LEAGUE_LOOKUP record was written for league "777" platform "ESPN" with canonical "canon-1"
    And the onboarder Lambda was invoked

  # Migration is not a premium feature; it must work without a subscription (BE-014).
  Scenario: Migration succeeds without an active subscription
    Given league "canon-1" has no subscription_end_time
    When I POST a migration of league "100" from "SLEEPER" to "ESPN" league "777"
    Then the API responds with status 202
    And a PLATFORM_MIGRATION item exists for league "canon-1"

  Scenario: Migrating to an already-onboarded destination returns 409
    Given a LEAGUE_LOOKUP exists for league "777" platform "ESPN" canonical "canon-2"
    When I POST a migration of league "100" from "SLEEPER" to "ESPN" league "777"
    Then the API responds with status 409

  Scenario: Malformed manager mapping is rejected before any write
    When I POST a migration of league "100" from "SLEEPER" to "ESPN" league "777" with an unknown mapping key
    Then the API responds with status 422
    And no PLATFORM_MIGRATION item exists for league "canon-1"
