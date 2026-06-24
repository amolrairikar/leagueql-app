Feature: AI weekly matchup recap generation (BE-022)
  The recap-generator Lambda backfills an AI recap for every completed week of
  every season a premium league has, idempotently and gated on the subscription.
  Bedrock is mocked; DynamoDB is real (moto), so the all-seasons enumeration,
  idempotent skip, and item writes are exercised end to end.

  Scenario: Backfills every week of every season for a premium league
    Given a premium league "canon-r" with matchups for seasons "2023,2024"
    When the recap generator runs for league "canon-r" on "SLEEPER"
    Then a MATCHUP_RECAP item exists for league "canon-r" season "2023" week "01"
    And a MATCHUP_RECAP item exists for league "canon-r" season "2023" week "02"
    And a MATCHUP_RECAP item exists for league "canon-r" season "2024" week "01"
    And the recap model generated 3 recaps

  Scenario: Re-running is a no-op (idempotent)
    Given a premium league "canon-r" with matchups for seasons "2023,2024"
    And the recap generator has already run for league "canon-r" on "SLEEPER"
    When the recap generator runs for league "canon-r" on "SLEEPER"
    Then the recap model generated 0 recaps

  Scenario: A non-premium league generates nothing
    Given a premium league "canon-r" with matchups for seasons "2023,2024"
    And league "canon-r" has subscription_end_time "1970-01-01T00:00:00+00:00"
    When the recap generator runs for league "canon-r" on "SLEEPER"
    Then no MATCHUP_RECAP items exist for league "canon-r"
    And the recap model generated 0 recaps
