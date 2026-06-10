Feature: Sleeper player stats refresh
  Scenarios exercise the deployed Sleeper player stats refresher Fargate task end to end. In
  production the task runs on a weekly CloudWatch Events schedule; it reads the player metadata
  from S3, fetches per-player season stats from Sleeper for every active player, and writes the
  aggregated stats back to S3.

  The test runs the deployed task via ECS RunTask with three container env-var overrides: a
  ``SEASON`` (so the refresh runs against the most recent completed season regardless of the
  live off-season state), a ``MAX_PLAYERS`` cap (so the end-to-end path — S3 read, live Sleeper
  fetch, aggregate, S3 write — is validated against a small subset in seconds rather than the
  full ~8,000-player, multi-minute run), and an ``OUTPUT_KEY`` pointing at an isolated test key
  (so the run never clobbers the production ``player-stats/sleeper_nfl_player_stats.json``
  cache). It relies on the player metadata file already present at the live S3 location, and
  cleans up the test object afterward.

  Scenario: Deployed refresher writes a capped stats subset to an isolated test key
    Given season, player-cap, and output-key overrides for the player stats refresher task
    When the deployed player stats refresher task is run to completion
    Then the task completes with a zero exit code
    And player stats for that season are written to the isolated test key for the active players
    And the production player stats cache is left untouched
