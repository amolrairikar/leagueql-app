Feature: Player metadata refresh writes to S3 (BE-010)
  The player-metadata Lambda conditionally fetches the Sleeper NFL players list
  and round-trips it through S3, where the processing pipeline later reads it.
  The external Sleeper HTTP boundary (NFL state + players endpoint) is mocked
  per scenario; S3 is moto-backed so the write is a real round-trip. The live
  Sleeper contract is covered separately by the daily integration canary.

  Scenario: Active season writes valid player metadata to S3
    Given the NFL state is the regular season
    And Sleeper returns a valid player metadata payload
    When the player metadata Lambda handler is invoked
    Then the handler completes without error
    And an object exists at the player metadata S3 key
    And the stored payload is a non-empty dict of valid player records

  Scenario: Offseason writes nothing to S3
    Given the NFL state is the offseason
    When the player metadata Lambda handler is invoked
    Then the handler completes without error
    And no object exists at the player metadata S3 key

  Scenario: A malformed Sleeper payload fails without writing to S3
    Given the NFL state is the regular season
    And Sleeper returns an empty payload
    When the player metadata Lambda handler is invoked
    Then the handler raises an error
    And no object exists at the player metadata S3 key
