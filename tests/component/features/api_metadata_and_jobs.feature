Feature: League metadata and job status APIs (BE-006, BE-008)
  GET /leagues/{id} returns onboarding status (never subscription-gated); GET
  /jobs/{id} returns lifecycle status with a missing job reported as FAILED.

  Scenario: Metadata is returned for an onboarded league regardless of subscription
    Given a LEAGUE_LOOKUP exists for league "100" platform "SLEEPER" canonical "canon-1"
    And league "canon-1" has subscription_end_time "2000-01-01T00:00:00+00:00"
    When I GET "/leagues/100?platform=SLEEPER"
    Then the API responds with status 200
    And the response data field "league_name" equals "Test League"
    And the response has Cache-Control "no-store"

  Scenario: An un-onboarded league returns 404
    When I GET "/leagues/404?platform=SLEEPER"
    Then the API responds with status 404

  Scenario: Opening a league records its last-accessed time (BE-018)
    Given a LEAGUE_LOOKUP exists for league "100" platform "SLEEPER" canonical "canon-1"
    When I GET "/leagues/100?platform=SLEEPER"
    Then the API responds with status 200
    And league "canon-1" has a last_accessed_at timestamp

  Scenario: A recently accessed league is not re-written within the throttle window (BE-018)
    Given a LEAGUE_LOOKUP exists for league "100" platform "SLEEPER" canonical "canon-1"
    And league "canon-1" was last accessed 5 minutes ago
    When I GET "/leagues/100?platform=SLEEPER"
    Then the API responds with status 200
    And league "canon-1" last_accessed_at is unchanged

  Scenario: A completed job reports COMPLETED
    Given a JOB_STATUS "COMPLETED" exists for job "11111111-1111-1111-1111-111111111111"
    When I GET "/jobs/11111111-1111-1111-1111-111111111111"
    Then the API responds with status 200
    And the job status is "COMPLETED"
    And the response has Cache-Control "no-store"

  Scenario: A failed job surfaces a failure reason
    Given a JOB_STATUS "FAILED" exists for job "22222222-2222-2222-2222-222222222222"
    When I GET "/jobs/22222222-2222-2222-2222-222222222222"
    Then the API responds with status 200
    And the job status is "FAILED"
    And the response data field "failure_code" equals "UPSTREAM"

  Scenario: A missing job is reported as FAILED so the frontend stops polling
    When I GET "/jobs/33333333-3333-3333-3333-333333333333"
    Then the API responds with status 200
    And the job status is "FAILED"
