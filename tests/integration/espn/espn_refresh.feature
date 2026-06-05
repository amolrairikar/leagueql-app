Feature: ESPN refresh integration
  ESPN refreshes reuse the onboarder Lambda with requestType REFRESH against the
  existing canonical league ID (there is no scheduled ESPN refresh job — refreshes
  are user-triggered). Scenarios test the full path from onboarder invocation
  through to DynamoDB status/metadata updates written by the downstream chain.

  Background:
    Given an ESPN league exists in DynamoDB

  Scenario: Successful ESPN refresh records completion in DynamoDB
    When the onboarder Lambda handler is invoked with an ESPN REFRESH request
    Then the handler returns statusCode 200 with status "succeeded"
    And DynamoDB shows job status "COMPLETED" for the test league
    And the last_refresh_at on the test league is updated within 5 minutes
