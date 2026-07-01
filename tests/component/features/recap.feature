Feature: AI weekly matchup recap generation (BE-022)
  The recap-generator Fargate task reads a premium league's pending marker, enumerates
  every season's completed weeks, and writes a MATCHUP_RECAP item for each missing week
  by calling the Anthropic API. The API call (generate_recap) is mocked; DynamoDB is real
  (moto), so the all-seasons enumeration, idempotent skip, queue marker lifecycle, and
  item writes are exercised end to end.

  Scenario: Generates a recap for every week of every season for a premium league
    Given a premium league "canon-r" with matchups for seasons "2023,2024"
    And a pending recap marker for league "canon-r"
    When the recap generator runs
    Then a MATCHUP_RECAP item exists for league "canon-r" season "2023" week "01"
    And a MATCHUP_RECAP item exists for league "canon-r" season "2023" week "02"
    And a MATCHUP_RECAP item exists for league "canon-r" season "2024" week "01"
    And the recap generator wrote 3 recaps
    And the recap queue marker for league "canon-r" is cleared

  Scenario: Re-running after a full pass is a no-op (idempotent)
    Given a premium league "canon-r" with matchups for seasons "2023,2024"
    And a pending recap marker for league "canon-r"
    And the recap generator has fully run for league "canon-r"
    And a pending recap marker for league "canon-r"
    When the recap generator runs
    Then the recap generator generated no recaps
    And the recap queue marker for league "canon-r" is cleared

  Scenario: A non-premium league produces nothing
    Given a premium league "canon-r" with matchups for seasons "2023,2024"
    And league "canon-r" has subscription_end_time "1970-01-01T00:00:00+00:00"
    And a pending recap marker for league "canon-r"
    When the recap generator runs
    Then the recap generator generated no recaps
    And no MATCHUP_RECAP items exist for league "canon-r"
    And the recap queue marker for league "canon-r" is cleared
