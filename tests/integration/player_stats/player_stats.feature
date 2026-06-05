Feature: Sleeper player stats refresh
  Scenarios exercise the deployed Sleeper player stats refresher Lambda end to end. In
  production the Lambda is triggered by an S3 event notification when the player metadata
  object is uploaded; it reads that metadata from S3, fetches per-player season stats from
  Sleeper for every active player, and writes the aggregated stats back to S3.

  The test invokes the deployed Lambda synchronously with a mocked S3 event notification
  carrying three overrides: a ``season`` (so the refresh runs against the most recent
  completed season regardless of the live off-season state), a ``max_players`` cap (so the
  end-to-end path — S3 read, live Sleeper fetch, aggregate, S3 write — is validated against a
  small subset in seconds rather than the full ~8,000-player, multi-minute run), and an
  ``output_key`` pointing at an isolated test key (so the run never clobbers the production
  ``player-stats/sleeper_nfl_player_stats.json`` cache). It relies on the player metadata file
  already present at the live S3 location, and cleans up the test object afterward.

  Scenario: Deployed refresher writes a capped stats subset to an isolated test key
    Given an S3 event notification for the player metadata object with season, player-cap, and output-key overrides
    When the deployed player stats refresher Lambda is invoked synchronously
    Then the invocation succeeds without a function error
    And player stats for that season are written to the isolated test key for the active players
    And the production player stats cache is left untouched
