Feature: AI weekly matchup recap batch pipeline (BE-022)
  The recap-drainer Lambda aggregates a premium league's missing weeks into a
  Bedrock batch job; the recap-completion Lambda writes a MATCHUP_RECAP item for
  every output record when the job finishes. Bedrock's submit + output are mocked;
  DynamoDB and S3 are real (moto), so the all-seasons enumeration, idempotent skip,
  manifest, queue markers, S3 input/output, and item writes are exercised end to end.

  Scenario: Drains and completes every week of every season for a premium league
    Given a premium league "canon-r" with matchups for seasons "2023,2024"
    And a pending recap marker for league "canon-r"
    When the recap drainer runs
    And Bedrock finishes the batch job
    And the recap completion runs for the job
    Then a MATCHUP_RECAP item exists for league "canon-r" season "2023" week "01"
    And a MATCHUP_RECAP item exists for league "canon-r" season "2023" week "02"
    And a MATCHUP_RECAP item exists for league "canon-r" season "2024" week "01"
    And the recap drainer submitted a job for 3 records
    And the recap queue marker for league "canon-r" is cleared

  Scenario: Re-draining after completion is a no-op (idempotent)
    Given a premium league "canon-r" with matchups for seasons "2023,2024"
    And a pending recap marker for league "canon-r"
    And the recap batch pipeline has fully run for league "canon-r"
    And a pending recap marker for league "canon-r"
    When the recap drainer runs
    Then the recap drainer submitted no job
    And the recap queue marker for league "canon-r" is cleared

  Scenario: A non-premium league drains to nothing
    Given a premium league "canon-r" with matchups for seasons "2023,2024"
    And league "canon-r" has subscription_end_time "1970-01-01T00:00:00+00:00"
    And a pending recap marker for league "canon-r"
    When the recap drainer runs
    Then the recap drainer submitted no job
    And no MATCHUP_RECAP items exist for league "canon-r"
    And the recap queue marker for league "canon-r" is cleared
