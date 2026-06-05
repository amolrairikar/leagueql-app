Feature: Sleeper onboarding integration
  Scenarios test the full onboarding path from onboarder handler invocation
  through to DynamoDB records written by the downstream Lambda chain.

  Scenario: Successful Sleeper league onboarding creates DynamoDB records
    When the onboarder Lambda handler is invoked with an ONBOARD request
    Then the handler returns statusCode 200 with status "succeeded"
    And DynamoDB shows job status "COMPLETED" for the test league
    And the LEAGUE_LOOKUP record exists in DynamoDB for the test league
