Feature: Yahoo onboarding integration
  Scenarios test the full onboarding path from onboarder handler invocation
  through to DynamoDB records written by the downstream Lambda chain. Yahoo data
  is fetched with the test owner's linked (KMS-encrypted) Yahoo OAuth token.

  Scenario: Successful Yahoo league onboarding creates DynamoDB records
    When the onboarder Lambda handler is invoked with a Yahoo ONBOARD request
    Then the handler returns statusCode 200 with status "succeeded"
    And DynamoDB shows job status "COMPLETED" for the test league
    And the LEAGUE_LOOKUP record exists in DynamoDB for the test league
