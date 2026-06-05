Feature: Sleeper player stats refresh
  Scenarios exercise the deployed Sleeper player stats refresher Lambda end to end. In
  production the Lambda is triggered by an S3 event notification when the player metadata
  object is uploaded; it reads that metadata from S3, fetches per-player season stats from
  Sleeper for every active player, and writes the aggregated stats back to S3.

  The test invokes the deployed Lambda synchronously with a mocked S3 event notification
  carrying a ``season`` override, so the refresh runs against the most recent completed
  season's full ~8,000-player dataset regardless of the live (off-season) NFL state. It
  relies on the player metadata file already present at the live S3 location, and because
  the run is rate-limited (~850 req/min) it can take several minutes to complete.

  Scenario: Deployed refresher writes full-season stats when invoked with a season override
    Given an S3 event notification for the player metadata object with a season override
    When the deployed player stats refresher Lambda is invoked synchronously
    Then the invocation succeeds without a function error
    And player stats for that season are written to S3 for the active players
