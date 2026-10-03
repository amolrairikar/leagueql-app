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
    And no lineup backfill is queued
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
    # backend/sleeper-transactions: only the two completed transactions are stored (the failed waiver is dropped).
    When I GET "/leagues/100/query?platform=SLEEPER&queryType=TRANSACTIONS#2024"
    Then the API responds with status 200
    And the query response has 2 row(s)
    # backend/data-processing-pipeline: the LEAGUE_SETTINGS view is extracted from the Sleeper
    # settings blob (playoff_teams=4, playoff_week_start=17 -> regular_season_weeks=16).
    When I GET "/leagues/100/query?platform=SLEEPER&queryType=LEAGUE_SETTINGS#2024"
    Then the API responds with status 200
    And the query response has 1 row(s)
    And a query response row has "num_playoff_teams" equal to "4"
    And a query response row has "playoff_week_start" equal to "17"
    And a query response row has "regular_season_weeks" equal to "16"

  Scenario: A Yahoo league onboards end to end and builds every view (backend/league-onboarding, backend/data-processing-pipeline, backend/yahoo-transactions)
    Given Yahoo player metadata and stats are cached in S3
    When the onboarder runs an ONBOARD for "YAHOO" league "431" with fixture "yahoo/raw_data_2024.json"
    Then the onboarder returns status 200
    And a LEAGUE_LOOKUP exists for onboarded league "431" platform "YAHOO"
    And a METADATA item exists for the onboarded league
    # backend/league-onboarding: weekly lineups are deferred to the lineup backfill.
    And the onboarded league has lineup-pending seasons "2024"
    And a lineup backfill is queued for the onboarded league
    When the processor processes the onboarded league
    Then a JOB_STATUS "COMPLETED" exists for the job
    And the league has at least one "TEAMS#2024" item
    And the league has at least one "MATCHUPS#2024" item
    And the league has at least one "STANDINGS#2024" item
    And the league has at least one "WEEKLY_STANDINGS#2024" item
    And the league has at least one "PLAYOFF_BRACKET#2024" item
    And the league has at least one "DRAFT#2024" item
    And the league has at least one "TRANSACTIONS#2024" item
    # backend/league-authorization: Yahoo reads are confidential (OAuth-gated), so only members
    # may query — the onboarding owner is a member.
    And the default caller is a member of the onboarded league
    # backend/data-processing-pipeline: Yahoo settings -> LEAGUE_SETTINGS (num_playoff_teams=4,
    # playoff_start_week=15 -> regular_season_weeks=14).
    When I GET "/leagues/431/query?platform=YAHOO&queryType=LEAGUE_SETTINGS#2024"
    Then the API responds with status 200
    And the query response has 1 row(s)
    And a query response row has "num_playoff_teams" equal to "4"
    And a query response row has "playoff_week_start" equal to "15"
    And a query response row has "regular_season_weeks" equal to "14"
    # backend/yahoo-transactions: the completed add/drop is stored (as a waiver — faab_bid present).
    When I GET "/leagues/431/query?platform=YAHOO&queryType=TRANSACTIONS#2024"
    Then the API responds with status 200
    And the query response has 1 row(s)

  Scenario: A Yahoo league with placement and consolation games names a single champion (backend/data-processing-pipeline, backend/yahoo-transactions)
    # A 6-team Yahoo bracket (weeks 15-17). The final week holds the title game (t10 v t12), a
    # 3rd-place game between the semifinal losers (t4 v t5) and consolation-bracket games between
    # teams that missed the playoffs. Only the title game is a championship game.
    Given Yahoo player metadata and stats are cached in S3
    When the onboarder runs an ONBOARD for "YAHOO" league "432" with fixture "yahoo/raw_data_2024_playoffs.json"
    Then the onboarder returns status 200
    And the default caller is a member of the onboarded league
    When the processor processes the onboarded league
    Then a JOB_STATUS "COMPLETED" exists for the job
    And the standings show only "Team 12" as champion
    And the "PLAYOFF_BRACKET#2024" bracket has exactly one championship game won by "423.l.432.t.12"
    # Consolation-bracket games are losers-tier; the 3rd-place game is a placement game.
    When I GET "/leagues/432/query?platform=YAHOO&queryType=MATCHUPS%232024%23WEEK%2317"
    Then the API responds with status 200
    And the query response has 4 row(s)
    And a query response row has "playoff_round" equal to "Finals"
    And a query response row has "playoff_round" equal to "Winners Consolation"
    And a query response row has "playoff_round" equal to "Losers Bracket"
    # A trade lists both teams; created is epoch ms and week comes from the week calendar
    # (the preseason trade clamps to week 1, the Sep-10 waiver lands in week 2).
    When I GET "/leagues/432/query?platform=YAHOO&queryType=TRANSACTIONS%232024"
    Then the API responds with status 200
    And the query response has 2 row(s)
    And a query response row has "type" equal to "trade"
    And a query response row has "created" equal to "1725400000000"
    And a query response row has "week" equal to "1"
    And a query response row has "week" equal to "2"

  Scenario: A large transactions season is chunked across items and round-trips through the query API (backend/sleeper-transactions)
    # backend/sleeper-transactions: a season with more transactions than fit in one DynamoDB
    # item is split across TRANSACTIONS#{season}#{chunk} items. A tiny per-item cap forces the
    # split with the small fixture; the query API must concatenate the chunks back into the
    # full row list with no row dropped or duplicated.
    Given Sleeper player metadata and stats are cached in S3
    And the transactions chunk size cap is 1 bytes
    When the onboarder runs an ONBOARD for "SLEEPER" league "600" with fixture "sleeper/raw_data_2024.json"
    Then the onboarder returns status 200
    When the processor processes the onboarded league
    Then a JOB_STATUS "COMPLETED" exists for the job
    And the league has more than one "TRANSACTIONS#2024#" item
    When I GET "/leagues/600/query?platform=SLEEPER&queryType=TRANSACTIONS#2024"
    Then the API responds with status 200
    And the query response has 2 row(s)

  Scenario: Reprocessing a legacy single-item transactions season does not duplicate rows (backend/sleeper-transactions)
    # backend/sleeper-transactions: a league onboarded before chunking has a single bare
    # TRANSACTIONS#{season} item. Reprocessing must delete that bare item before writing the
    # chunk items, so the prefix read returns each row exactly once — never the bare item's
    # rows plus the chunks'.
    Given Sleeper player metadata and stats are cached in S3
    When the onboarder runs an ONBOARD for "SLEEPER" league "700" with fixture "sleeper/raw_data_2024.json"
    Then the onboarder returns status 200
    Given a legacy bare "TRANSACTIONS#2024" item with 2 row(s) exists for the onboarded league
    When the processor processes the onboarded league
    Then a JOB_STATUS "COMPLETED" exists for the job
    # If the bare item were not deleted, the prefix read would return its 2 rows on top of
    # the 2 rebuilt chunk rows (4 total); exactly 2 proves the bare item was removed.
    When I GET "/leagues/700/query?platform=SLEEPER&queryType=TRANSACTIONS#2024"
    Then the API responds with status 200
    And the query response has 2 row(s)

  Scenario: An ESPN league onboards and builds current-season transactions across every week (backend/espn-transactions)
    # ESPN transactions are fetched per scoring period (transactions_week{N}); EXECUTED
    # waivers/free agents from every week are compiled into TRANSACTIONS#{season} items
    # and round-trip through the query API, with players/teams resolved. The fixture
    # carries a week-1 waiver and a week-2 free agent to prove multi-week collection,
    # plus a duplicate of the free agent in a later week (ESPN echoes the current
    # period's transactions for requests at or beyond it) to prove dedup — the query
    # returns 2 distinct rows, not 3.
    When the onboarder runs an ONBOARD for "ESPN" league "800" with fixture "espn/raw_data_2024.json"
    Then the onboarder returns status 200
    And the default caller is a member of the onboarded league
    When the processor processes the onboarded league
    Then a JOB_STATUS "COMPLETED" exists for the job
    And the league has at least one "TRANSACTIONS#2024" item
    When I GET "/leagues/800/query?platform=ESPN&queryType=TRANSACTIONS#2024"
    Then the API responds with status 200
    And the query response has 2 row(s)
    And a query response row has "type" equal to "free_agent"
    And a query response row has "type" equal to "waiver"
    And a query response row has "week" equal to "1"
    And a query response row has "week" equal to "2"

  Scenario: An ESPN league with no current-season transactions writes no TRANSACTIONS item (backend/espn-transactions)
    When the onboarder runs an ONBOARD for "ESPN" league "810" with fixture "espn/raw_data_no_transactions_2024.json"
    Then the onboarder returns status 200
    And the default caller is a member of the onboarded league
    When the processor processes the onboarded league
    Then a JOB_STATUS "COMPLETED" exists for the job
    When I GET "/leagues/810/query?platform=ESPN&queryType=TRANSACTIONS#2024"
    Then the API responds with status 404

  Scenario: An ESPN league onboards its accessible seasons and skips a season whose fetch failed (backend/league-onboarding)
    # The user can access 2024 but not 2023 (a 401 nulls one of 2023's fetches). The
    # fully-successful 2024 season onboards while 2023 is dropped — no S3 payload, no
    # processed views — and the onboard still succeeds.
    When the onboarder runs an ONBOARD for "ESPN" league "820" with fixture "espn/raw_data_multiseason.json" where season "2023" fails
    Then the onboarder returns status 200
    And the default caller is a member of the onboarded league
    When the processor processes the onboarded league
    Then a JOB_STATUS "COMPLETED" exists for the job
    And the league has at least one "STANDINGS#2024" item
    And the league has exactly 0 "STANDINGS#2023" item(s)

  Scenario: An ESPN onboard where every season's fetch fails records a FAILED job and writes no METADATA (backend/league-onboarding)
    # When no season can be fetched, the onboard fails as a whole (the existing UPSTREAM/502
    # path) and writes nothing.
    When the onboarder runs an ONBOARD for "ESPN" league "830" with fixture "espn/raw_data_2024.json" where every season fails
    Then the onboarder returns status 502
    And a JOB_STATUS "FAILED" exists for the job
    And the JOB_STATUS failure_code is "UPSTREAM"
    And no METADATA item exists for the onboarded league

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

  Scenario: A failed MIGRATE destination fetch writes no destination LEAGUE_LOOKUP (SEC-01)
    # The destination LEAGUE_LOOKUP is written by the onboarder only after a successful
    # destination fetch, so a migration whose fetch fails leaves the destination league
    # ID unclaimed and still onboardable by its legitimate owner.
    When the onboarder fails a MIGRATE destination fetch for league "888" canonical "canon-mig"
    Then the onboarder returns status 502
    And a JOB_STATUS "FAILED" exists for the job
    And no LEAGUE_LOOKUP record exists for league "888" platform "ESPN"

  Scenario: A brand-new undrafted ESPN league fails NOT_STARTED and writes no data (backend/league-onboarding)
    # ESPNClient excludes a not-yet-drafted latest season; a league whose only season
    # hasn't drafted resolves to no seasons, so ONBOARD is a NOT_STARTED user error with
    # nothing written — mirroring the Sleeper pre_draft behavior.
    When the onboarder runs an ONBOARD for an ESPN league that has not drafted
    Then the onboarder returns status 400
    And a JOB_STATUS "FAILED" exists for the job
    And the JOB_STATUS failure_code is "NOT_STARTED"
    And no METADATA item exists for the onboarded league

  Scenario: The Yahoo lineup backfill fills in weekly player points (backend/yahoo-lineup-backfill, backend/data-processing-pipeline)
    Given Yahoo player metadata and stats are cached in S3
    When the onboarder runs an ONBOARD for "YAHOO" league "433" with fixture "yahoo/raw_data_2024_no_rosters.json"
    Then the onboarder returns status 200
    And the onboarded league has lineup-pending seasons "2024"
    And a lineup backfill is queued for the onboarded league
    And the default caller is a member of the onboarded league
    When the processor processes the onboarded league
    And the lineup backfill runs with Yahoo rosters from fixture "yahoo/backfill_rosters_2024.json"
    Then the lineup backfill outcome is "completed"
    And the lineup store for season "2024" has weeks "1,15"
    And the manifest asks the processor to rebuild season "2024"
    And the onboarded league has no lineup-pending seasons
    When the processor processes the onboarded league
    Then the league has at least one "MATCHUPS#2024" item
    When I GET "/leagues/433/query?platform=YAHOO&queryType=MATCHUPS%232024%23WEEK%2301"
    Then the API responds with status 200
    And the week 1 matchup lists "Josh QB" as a starter with 25 points

  Scenario: A league deleted mid-backfill is dropped without leaving data behind (backend/yahoo-lineup-backfill, backend/delete-league)
    When the onboarder runs an ONBOARD for "YAHOO" league "435" with fixture "yahoo/raw_data_2024_no_rosters.json"
    And the league is deleted while the lineup backfill fetches Yahoo rosters from fixture "yahoo/backfill_rosters_2024.json"
    Then the lineup backfill outcome is "league_deleted"
    And no METADATA item exists for the onboarded league
    And no lineup store exists for the onboarded league

  Scenario: A throttled Yahoo lineup backfill leaves the season pending and retries later (backend/yahoo-lineup-backfill)
    When the onboarder runs an ONBOARD for "YAHOO" league "434" with fixture "yahoo/raw_data_2024_no_rosters.json"
    And the lineup backfill runs and Yahoo throttles it
    Then the lineup backfill outcome is "throttled"
    And the onboarded league has lineup-pending seasons "2024"
    And a throttled lineup backfill retry is queued for the onboarded league

  Scenario: A Yahoo league whose manager slots change across seasons keeps one owner per person (backend/data-processing-pipeline, backend/league-onboarding)
    # Yahoo masks every guid, so per-league manager_ids are slots. Slot 2 changes hands between
    # seasons (Manager B wins 2023, leaves; Manager C takes slot 2 and wins 2024) and Managers A
    # and D swap slots. Each title must land on its real winner, not the slot.
    Given Yahoo player metadata and stats are cached in S3
    When the onboarder runs an ONBOARD for "YAHOO" league "436" with fixture "yahoo/raw_data_slot_changes.json"
    Then the onboarder returns status 200
    When the processor processes the onboarded league
    Then a JOB_STATUS "COMPLETED" exists for the job
    And the "STANDINGS#2023" champion is "Manager B"
    And the "STANDINGS#2024" champion is "Manager C"
    And the "STANDINGS#2023" and "STANDINGS#2024" champions have different owner ids
    And "Manager A" has the same owner id in "STANDINGS#2023" and "STANDINGS#2024"
    And "Manager D" has the same owner id in "STANDINGS#2023" and "STANDINGS#2024"

  Scenario: A latest-season Yahoo refresh keeps each manager's owner id (backend/data-processing-pipeline)
    Given Yahoo player metadata and stats are cached in S3
    When the onboarder runs an ONBOARD for "YAHOO" league "437" with fixture "yahoo/raw_data_slot_changes.json"
    And the processor processes the onboarded league
    And I remember the owner ids in "STANDINGS#2024"
    When the onboarder runs a REFRESH for "YAHOO" league "437" with fixture "yahoo/raw_data_slot_changes_2024.json"
    And the processor processes the onboarded league
    Then a JOB_STATUS "COMPLETED" exists for the job
    And the owner ids in "STANDINGS#2024" are unchanged
    And "Manager A" has the same owner id in "STANDINGS#2023" and "STANDINGS#2024"

  Scenario: A backfill still rebuilds every season when the lineup backfill rewrites the manifest first (backend/data-processing-pipeline)
    # The backfill's manifest write (reprocess_all) is copied by the lineup backfill
    # (reprocess_seasons=2024) before the processor run it triggered reads the manifest. That run
    # must still act on its own version: rebuild every season under the backfill's job.
    Given Yahoo player metadata and stats are cached in S3
    When the onboarder runs an ONBOARD for "YAHOO" league "438" with fixture "yahoo/raw_data_slot_changes.json"
    And the processor processes the onboarded league
    And the "STANDINGS#2023" item is deleted
    And the onboarder runs a backfill REFRESH for "YAHOO" league "438" with fixture "yahoo/raw_data_slot_changes_2024.json"
    And I remember the current manifest version
    And the lineup backfill republishes season "2024" before the processor runs
    And the processor processes the remembered manifest version
    Then a JOB_STATUS "COMPLETED" exists for the job
    And the league has at least one "STANDINGS#2023" item
