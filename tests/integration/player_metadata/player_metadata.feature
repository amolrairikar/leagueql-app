Feature: Player metadata refresh
  Scenarios test the player metadata Lambda handler which conditionally
  fetches NFL player data from Sleeper and writes it to S3.

  Scenario: Handler skips S3 write during NFL offseason
    Given the NFL state API returns off-season
    When the player metadata Lambda handler is invoked
    Then the handler returns without error

  Scenario: Handler fetches and writes player metadata during active season
    Given the NFL state API returns week 5 of the regular season
    When the player metadata Lambda handler is invoked
    Then player metadata is written to S3 with valid player records
