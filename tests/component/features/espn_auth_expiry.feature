Feature: Alert the owner when auto-refresh ESPN cookies expire (backend/espn-credential-storage)
  When a scheduled ESPN refresh is rejected with the owner's stored cookies, the onboarder records
  ESPN_AUTH without paging, flags the stored cookies, and the owner is told to re-enter them on
  their next visit. The scheduled refresh skips the league until the cookies are re-stored, which
  clears the flag.

  Scenario: A scheduled refresh rejected by ESPN flags the cookies and alerts the owner
    Given an auto-refresh ESPN league "600" canonical "canon-6" season "2024" owner "owner_user"
    And the default user has stored ESPN cookies
    When the scheduled refresh runs for ESPN league "600" canonical "canon-6" and ESPN rejects every request
    Then the onboarder returns status 502
    And the JOB_STATUS failure_code is "ESPN_AUTH"
    And no onboarder failure alert was published
    And the default user's stored ESPN cookies are flagged as rejected
    When I GET "/leagues/600?platform=ESPN"
    Then the API responds with status 200
    And the response data field "espn_reauth_required" equals "True"
    And the response data field "espn_credentials_failed_at" is present
    When the auto-refresh runs with NFL state season_type "regular" week "10"
    Then the auto-refresh response status is "succeeded"
    And the onboarder was invoked 0 time(s)

  Scenario: Re-entering cookies on a blocked opted-in refresh clears the alert
    Given a LEAGUE_LOOKUP exists for league "500" platform "ESPN" canonical "canon-e"
    And league "canon-e" is opted into auto-refresh
    And the default user's stored ESPN cookies were rejected by ESPN
    When I GET "/leagues/500?platform=ESPN"
    Then the response data field "espn_reauth_required" equals "True"
    Given league "canon-e" was last refreshed 2 days ago
    And ESPN responds to the cookie check with status 200
    When I POST an auto-refresh opted-in REFRESH of league "500" on "ESPN"
    Then the API responds with status 429
    And the default user's stored ESPN cookies decrypt to the submitted cookies
    When I GET "/leagues/500?platform=ESPN"
    Then the response data field "espn_reauth_required" equals "False"
    And the response data field "espn_credentials_failed_at" is null
