Feature: Onboard-to-processed pipeline (backend/league-onboarding, backend/data-processing-pipeline)
  Drives the onboarder and processor as one component with the platform API
  mocked. The onboarder writes raw data to (moto) S3 and league records to
  DynamoDB; a synthesized S3 event then runs the processor, whose DuckDB
  transforms build the precomputed views read by the API.

  Scenario: A Sleeper league onboards end to end and builds every view
    Given Sleeper player metadata and stats are cached in S3
    When the onboarder runs an ONBOARD for "SLEEPER" league "100" with fixture "sleeper/raw_data_2024.json"
    Then the onboarder returns status 200
    And a LEAGUE_LOOKUP exists for onboarded league "100" platform "SLEEPER"
    And a METADATA item exists for the onboarded league
    When the processor processes the onboarded league
    Then a JOB_STATUS "COMPLETED" exists for the job
    And the league has at least one "TEAMS#2024" item
    And the league has at least one "MATCHUPS#2024" item
    And the league has at least one "STANDINGS#2024" item
    And the league has at least one "WEEKLY_STANDINGS#2024" item
    And the league has at least one "PLAYOFF_BRACKET#2024" item
    And the league has at least one "DRAFT#2024" item
    And the league has at least one "TRANSACTIONS#2024" item
    And the standings show "Team Alice" as champion
    And the LEAGUE_COUNT is 1
    # backend/sleeper-transactions: only the two completed transactions are stored (the failed waiver is dropped).
    When I GET "/leagues/100/query?platform=SLEEPER&queryType=TRANSACTIONS#2024"
    Then the API responds with status 200
    And the query response has 2 row(s)

  Scenario: Onboarding a renewed Sleeper season reuses the existing league without a duplicate METADATA (backend/league-onboarding)
    # A Sleeper league renews under a new league ID linked by previous_league_id. Onboarding
    # it must fold into the existing canonical league, registering the new ID's LEAGUE_LOOKUP
    # and preserving the original METADATA — never creating a second, separate league.
    Given Sleeper player metadata and stats are cached in S3
    And a LEAGUE_LOOKUP exists for league "100" platform "SLEEPER" canonical "canon-prior"
    And the Sleeper previous_league_id chain resolves to canonical "canon-prior"
    When the onboarder runs an ONBOARD for "SLEEPER" league "200" with fixture "sleeper/raw_data_2024.json"
    Then the onboarder returns status 200
    And a LEAGUE_LOOKUP exists for onboarded league "200" platform "SLEEPER"
    And exactly one un-overwritten METADATA exists for canonical "canon-prior"

  Scenario: Onboarding an offseason Sleeper renewal registers a pending lookup (backend/league-onboarding, backend/scheduled-sleeper-auto-refresh)
    # The renewed season hasn't started (pre_draft), so there's nothing to process yet, but
    # the new league ID must still be persisted (pointing at the existing canonical, marked
    # pending) so the scheduled auto-refresh can attach the season once it begins.
    Given Sleeper player metadata and stats are cached in S3
    And a LEAGUE_LOOKUP exists for league "100" platform "SLEEPER" canonical "canon-prior"
    And the Sleeper previous_league_id chain resolves to canonical "canon-prior"
    When the onboarder runs an ONBOARD for "SLEEPER" league "200" with no started seasons pending "2026"
    Then the onboarder returns status 200
    And a pending LEAGUE_LOOKUP exists for league "200" pending season "2026" canonical "canon-prior"
    And exactly one un-overwritten METADATA exists for canonical "canon-prior"

  Scenario: A Sleeper league with no playoffs yet onboards without a bracket (backend/league-onboarding, backend/data-processing-pipeline)
    # Sleeper returns a null winners_bracket/losers_bracket before a season reaches the
    # playoffs. That is a valid state and must not fail onboarding — the season simply
    # produces no PLAYOFF_BRACKET item while every other view is still built.
    Given Sleeper player metadata and stats are cached in S3
    When the onboarder runs an ONBOARD for "SLEEPER" league "300" with fixture "sleeper/raw_data_2024_null_bracket.json"
    Then the onboarder returns status 200
    And a METADATA item exists for the onboarded league
    When the processor processes the onboarded league
    Then a JOB_STATUS "COMPLETED" exists for the job
    And the league has at least one "STANDINGS#2024" item
    And the league has exactly 0 "PLAYOFF_BRACKET#2024" item(s)
    # Week 17 is a playoff week (playoff_week_start=17), but with no bracket its games must
    # not be mislabelled as losers-bracket games — they stay regular season.
    When I GET "/leagues/300/query?platform=SLEEPER&queryType=MATCHUPS#2024#WEEK#17"
    Then the API responds with status 200
    And no query response row has "playoff_round" equal to "Losers Bracket"

  Scenario: A preseason Sleeper league with no player stats yet builds DRAFT without erroring (backend/data-processing-pipeline)
    # A new Sleeper season created before its first games have been played has player
    # metadata but no accumulated stats, so player_scoring_totals computes to no rows. The
    # empty-view guard must register it as a typed 0-row view so the DRAFT (SLEEPER)
    # transform still binds (yielding draft rows with no scoring) instead of crashing the
    # whole run on a 0-column DataFrame.
    Given Sleeper player metadata is cached in S3 with no player stats
    When the onboarder runs an ONBOARD for "SLEEPER" league "400" with fixture "sleeper/raw_data_2024.json"
    Then the onboarder returns status 200
    And a METADATA item exists for the onboarded league
    When the processor processes the onboarded league
    Then a JOB_STATUS "COMPLETED" exists for the job
    And the league has at least one "DRAFT#2024" item
    And the league has at least one "STANDINGS#2024" item

  Scenario: An unplayed 0-0 regular-season week is excluded from standings but still stored (backend/data-processing-pipeline)
    # An in-progress season persists future/unplayed weeks as 0-0 placeholder matchups
    # (winner="TIE"). These must not be counted as tied games in STANDINGS/WEEKLY_STANDINGS,
    # yet the MATCHUPS view must still store the 0-0 rows (a future live-odds sim replays them).
    Given Sleeper player metadata and stats are cached in S3
    When the onboarder runs an ONBOARD for "SLEEPER" league "500" with fixture "sleeper/raw_data_2024_unplayed_week.json"
    Then the onboarder returns status 200
    And a METADATA item exists for the onboarded league
    When the processor processes the onboarded league
    Then a JOB_STATUS "COMPLETED" exists for the job
    # Weeks 1-2 are played; week 3 is an unplayed 0-0 week. Each team's standings count only the
    # two played weeks — no phantom tie or extra game from week 3.
    And every "STANDINGS#2024" row shows games_played 2 and ties 0
    And no "WEEKLY_STANDINGS#2024" row is for week "3"
    # The 0-0 placeholder rows are still written to the matchups view.
    And the league has at least one "MATCHUPS#2024#WEEK#03" item
    And the "MATCHUPS#2024#WEEK#03" item stores an unplayed 0-0 matchup

  Scenario: An upstream auth failure records a FAILED job and writes no METADATA
    When the onboarder fails to reach the platform
    Then the onboarder returns status 502
    And a JOB_STATUS "FAILED" exists for the job
    And the JOB_STATUS failure_code is "ESPN_AUTH"
    And no METADATA item exists for the onboarded league
