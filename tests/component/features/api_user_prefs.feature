Feature: User league preferences API (backend/user-league-preferences)
  GET/PUT /leagues/{id}/me store each caller's claimed team in the league's partition.

  Background:
    Given a LEAGUE_LOOKUP exists for league "100" platform "SLEEPER" canonical "canon-1"
    And league "canon-1" has teams owned by "U1, U2"

  Scenario: No claim yet
    When I GET "/leagues/100/me?platform=SLEEPER"
    Then the API responds with status 200
    And the response data field "owner_id" is null

  Scenario: Claim a team and read it back
    When I PUT my claimed owner "U2" for "/leagues/100/me?platform=SLEEPER"
    Then the API responds with status 200
    When I GET "/leagues/100/me?platform=SLEEPER"
    Then the response data field "owner_id" equals "U2"

  Scenario: An unknown owner is rejected and the claim is unchanged
    Given I PUT my claimed owner "U1" for "/leagues/100/me?platform=SLEEPER"
    When I PUT my claimed owner "ZZ" for "/leagues/100/me?platform=SLEEPER"
    Then the API responds with status 400
    When I GET "/leagues/100/me?platform=SLEEPER"
    Then the response data field "owner_id" equals "U1"

  Scenario: Claims are per user
    Given I PUT my claimed owner "U1" for "/leagues/100/me?platform=SLEEPER"
    And the request is authenticated as "other_user"
    When I GET "/leagues/100/me?platform=SLEEPER"
    Then the response data field "owner_id" is null

  Scenario: Non-members of a gated league cannot claim
    Given a LEAGUE_LOOKUP exists for league "500" platform "ESPN" canonical "canon-e"
    And league "canon-e" has teams owned by "E1"
    And the request is authenticated as "stranger"
    When I PUT my claimed owner "E1" for "/leagues/500/me?platform=ESPN"
    Then the API responds with status 403
    And no preferences exist for user "stranger" in league "canon-e"

  Scenario: Deleting the league removes claims
    Given I PUT my claimed owner "U1" for "/leagues/100/me?platform=SLEEPER"
    When I DELETE "/leagues/100?platform=SLEEPER"
    Then the API responds with status 200
    And no DynamoDB items remain for league "canon-1"
