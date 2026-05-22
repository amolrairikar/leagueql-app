Feature: Sleeper refresh integration
  Scenarios test the full dispatch path from sleeper_refresh handler
  through to DynamoDB status updates written by the downstream Lambda chain.

  Background:
    Given the NFL state API returns week 3 of the regular season

  Scenario: Successful refresh dispatches leagues and records completion in DynamoDB
    Given a Sleeper league exists in DynamoDB
    When the sleeper refresh Lambda handler is invoked
    Then the handler returns statusCode 200 with status "succeeded"
    And DynamoDB shows refresh_status "COMPLETED" for the test league
    And the last_refresh_at is within 5 minutes of the current time

  Scenario: Handler skips refresh when NFL season is off-season
    Given the NFL state API returns off-season
    When the sleeper refresh Lambda handler is invoked
    Then the handler returns statusCode 200 with status "skipped"

  Scenario: Handler skips refresh during week 1
    Given the NFL state API returns week 1 of the regular season
    When the sleeper refresh Lambda handler is invoked
    Then the handler returns statusCode 200 with status "skipped"
