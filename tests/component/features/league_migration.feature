Feature: League migration API (backend/league-migration)
  POST /leagues/{id}/migrate records the manager mapping and triggers the onboarder,
  preserving all-time history under one canonical league. The destination LEAGUE_LOOKUP
  is written by the onboarder only after it successfully fetches the destination league
  (SEC-01), so the API itself never writes it up front.

  Background:
    Given a LEAGUE_LOOKUP exists for league "100" platform "SLEEPER" canonical "canon-1"

  Scenario: Migration records the mapping and triggers the onboarder without writing the destination lookup
    When I POST a migration of league "100" from "SLEEPER" to "ESPN" league "777"
    Then the API responds with status 202
    And a PLATFORM_MIGRATION item exists for league "canon-1"
    And no LEAGUE_LOOKUP record exists for league "777" platform "ESPN"
    And the onboarder Lambda was invoked

  Scenario: Migrating to an already-onboarded destination returns 409
    Given a LEAGUE_LOOKUP exists for league "777" platform "ESPN" canonical "canon-2"
    When I POST a migration of league "100" from "SLEEPER" to "ESPN" league "777"
    Then the API responds with status 409

  Scenario: Malformed manager mapping is rejected before any write
    When I POST a migration of league "100" from "SLEEPER" to "ESPN" league "777" with an unknown mapping key
    Then the API responds with status 422
    And no PLATFORM_MIGRATION item exists for league "canon-1"

  Scenario: Migrating to a Yahoo destination without a linked account returns 403
    When I POST a Yahoo migration of league "100" from "SLEEPER" to league "456" without a link
    Then the API responds with status 403
    And no PLATFORM_MIGRATION item exists for league "canon-1"

  Scenario: Migrating to a linked Yahoo destination records the mapping and triggers the onboarder
    When I POST a Yahoo migration of league "100" from "SLEEPER" to league "456" with a linked account
    Then the API responds with status 202
    And a PLATFORM_MIGRATION item exists for league "canon-1"
    And the onboarder Lambda was invoked
