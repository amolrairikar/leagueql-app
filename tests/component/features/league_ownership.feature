Feature: League ownership and ESPN read authorization (backend/league-authorization)
  Mutations are owner-gated; ESPN league data is confidential, so reads are
  member-gated with a cookie-verified join. Sleeper reads stay open.

  Background:
    Given a LEAGUE_LOOKUP exists for league "100" platform "ESPN" canonical "canon-1"

  Scenario: The owner can read an ESPN league and is flagged as owner
    Given the request is authenticated as "owner_user"
    When I GET "/leagues/100?platform=ESPN"
    Then the API responds with status 200
    And the response data field "is_owner" equals "True"

  Scenario: A non-member cannot read an ESPN league
    Given the request is authenticated as "stranger"
    When I GET "/leagues/100?platform=ESPN"
    Then the API responds with status 403

  Scenario: A non-member cannot query an ESPN league's data
    Given league "canon-1" has a "MATCHUPS#2024#WEEK#01" view with 1 row(s)
    And the request is authenticated as "stranger"
    When I GET "/leagues/100/query?platform=ESPN&queryType=MATCHUPS"
    Then the API responds with status 403

  Scenario: A non-member joins by verifying ESPN cookies, then can read
    Given the request is authenticated as "league_mate"
    When I POST to verify-membership for league "100" with ESPN returning 200
    Then the API responds with status 200
    And user "league_mate" is a member of league "canon-1"
    When I GET "/leagues/100?platform=ESPN"
    Then the API responds with status 200
    And the response data field "is_owner" equals "False"

  Scenario: Verification fails when ESPN rejects the cookies
    Given the request is authenticated as "imposter"
    When I POST to verify-membership for league "100" with ESPN returning 401
    Then the API responds with status 403
    And user "imposter" is not a member of league "canon-1"

  Scenario: Verification is rejected for Sleeper leagues
    Given a LEAGUE_LOOKUP exists for league "200" platform "SLEEPER" canonical "canon-2"
    And the request is authenticated as "anyone"
    When I POST to verify-membership for "SLEEPER" league "200" with ESPN returning 200
    Then the API responds with status 400

  Scenario: A Sleeper league stays open to any authenticated user
    Given a LEAGUE_LOOKUP exists for league "200" platform "SLEEPER" canonical "canon-2"
    And the request is authenticated as "stranger"
    When I GET "/leagues/200?platform=SLEEPER"
    Then the API responds with status 200

  Scenario: Ownership handoff via a one-time token
    Given the request is authenticated as "owner_user"
    When I POST a transfer token for league "100" on "ESPN"
    Then the API responds with status 200
    # The secret token response falls back to the default-deny cache policy (backend/security-headers).
    And the response has Cache-Control "no-store"
    Given the request is authenticated as "new_owner"
    When I claim ownership of league "100" on "ESPN" with the minted token
    Then the API responds with status 200
    And user "new_owner" is the owner of league "canon-1"
    Given the request is authenticated as "owner_user"
    When I DELETE "/leagues/100?platform=ESPN"
    Then the API responds with status 403

  Scenario: Claiming with a wrong token is forbidden
    Given the request is authenticated as "owner_user"
    When I POST a transfer token for league "100" on "ESPN"
    Then the API responds with status 200
    Given the request is authenticated as "new_owner"
    When I claim ownership of league "100" on "ESPN" with token "not-the-token"
    Then the API responds with status 403
