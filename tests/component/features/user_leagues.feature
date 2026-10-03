Feature: Per-user league membership index (backend/user-leagues)
  Each (league, user) pair gets a MEMBER item that the sparse GSI4 index uses to
  list a user's leagues. Items are written on onboard, invite redemption, ownership
  claim, and Sleeper open, and are swept with the league on delete.

  Scenario: The onboarding owner is indexed with the league
    When user "owner_user" onboards "SLEEPER" league "100" with fixture "sleeper/raw_data_2024.json"
    Then the onboarder returns status 200
    And user "owner_user" is indexed for the onboarded league

  Scenario: A system onboard indexes no one
    When the onboarder runs an ONBOARD for "SLEEPER" league "100" with fixture "sleeper/raw_data_2024.json"
    Then the onboarder returns status 200
    And the onboarded league indexes no one

  Scenario: Redeeming an invite indexes the member once
    Given a LEAGUE_LOOKUP exists for league "100" platform "ESPN" canonical "canon-1"
    And the request is authenticated as "owner_user"
    When I POST an invite token for league "100" on "ESPN"
    Then the API responds with status 200
    Given the request is authenticated as "league_mate"
    When I accept the invite for league "100" on "ESPN" with the minted token
    Then the API responds with status 200
    When I accept the invite for league "100" on "ESPN" with the minted token
    Then the API responds with status 200
    And user "league_mate" is indexed for league "canon-1"

  Scenario: Claiming ownership indexes the new owner and keeps the previous one
    Given a LEAGUE_LOOKUP exists for league "100" platform "ESPN" canonical "canon-1"
    And user "owner_user" is indexed for league "canon-1"
    And the request is authenticated as "owner_user"
    When I POST a transfer token for league "100" on "ESPN"
    Then the API responds with status 200
    Given the request is authenticated as "new_owner"
    When I claim ownership of league "100" on "ESPN" with the minted token
    Then the API responds with status 200
    And user "new_owner" is indexed for league "canon-1"
    And user "owner_user" is indexed for league "canon-1"

  Scenario: Opening a Sleeper league indexes the viewer
    Given a LEAGUE_LOOKUP exists for league "200" platform "SLEEPER" canonical "canon-2"
    And the request is authenticated as "stranger"
    When I GET "/leagues/200?platform=SLEEPER"
    Then the API responds with status 200
    When I GET "/leagues/200?platform=SLEEPER"
    Then the API responds with status 200
    And user "stranger" is indexed for league "canon-2"

  Scenario: Opening an ESPN league writes no index entry
    Given a LEAGUE_LOOKUP exists for league "100" platform "ESPN" canonical "canon-1"
    When I GET "/leagues/100?platform=ESPN"
    Then the API responds with status 200
    And user "owner_user" is not indexed for league "canon-1"

  Scenario: Deleting a league removes every index entry
    Given a LEAGUE_LOOKUP exists for league "200" platform "SLEEPER" canonical "canon-2"
    And user "owner_user" is indexed for league "canon-2"
    And user "viewer" is indexed for league "canon-2"
    When I DELETE "/leagues/200?platform=SLEEPER"
    Then the API responds with status 200
    And user "owner_user" is not indexed for league "canon-2"
    And user "viewer" is not indexed for league "canon-2"

  Scenario: GET /me/leagues lists a league the caller onboarded
    When user "owner_user" onboards "SLEEPER" league "100" with fixture "sleeper/raw_data_2024.json"
    Then the onboarder returns status 200
    Given the request is authenticated as "owner_user"
    When I GET "/me/leagues"
    Then the API responds with status 200
    And the response has Cache-Control "no-store"
    And my leagues list league "100" on "SLEEPER"

  Scenario: GET /me/leagues includes a league joined by invite
    Given a LEAGUE_LOOKUP exists for league "100" platform "ESPN" canonical "canon-1"
    And the request is authenticated as "owner_user"
    When I POST an invite token for league "100" on "ESPN"
    Then the API responds with status 200
    Given the request is authenticated as "league_mate"
    When I accept the invite for league "100" on "ESPN" with the minted token
    Then the API responds with status 200
    When I GET "/me/leagues"
    Then the API responds with status 200
    And my leagues list league "100" on "ESPN"

  Scenario: GET /me/leagues with no leagues returns an empty list
    Given the request is authenticated as "newcomer"
    When I GET "/me/leagues"
    Then the API responds with status 200
    And my leagues list is empty

  Scenario: GET /me/leagues requires authentication
    Given the request is unauthenticated
    When I GET "/me/leagues"
    Then the API responds with status 401
