Feature: Delete league API (backend/delete-league)
  DELETE /leagues/{id} sweeps all canonical-keyed items + S3 objects.

  Background:
    Given a LEAGUE_LOOKUP exists for league "100" platform "SLEEPER" canonical "canon-1"
    And league "canon-1" has a "STANDINGS#2024" view with 2 row(s)
    And league "canon-1" has raw data stored in S3

  Scenario: Delete sweeps all data
    When I DELETE "/leagues/100?platform=SLEEPER"
    Then the API responds with status 200
    And the API response detail is "Successfully deleted league"
    And no DynamoDB items remain for league "canon-1"

  Scenario: An un-onboarded league returns 404
    When I DELETE "/leagues/404?platform=SLEEPER"
    Then the API responds with status 404

  Scenario: Deleting the owner's last Yahoo league removes their stored OAuth token
    Given a LEAGUE_LOOKUP exists for league "300" platform "YAHOO" canonical "canon-y"
    And a YAHOO_OAUTH token item exists for the default user
    When I DELETE "/leagues/300?platform=YAHOO"
    Then the API responds with status 200
    And no YAHOO_OAUTH token item exists for the default user

  Scenario: Deleting a Yahoo league keeps the OAuth token when another Yahoo league remains
    Given a LEAGUE_LOOKUP exists for league "300" platform "YAHOO" canonical "canon-y"
    And an onboarded YAHOO league "canon-y2" owned by the default user
    And a YAHOO_OAUTH token item exists for the default user
    When I DELETE "/leagues/300?platform=YAHOO"
    Then the API responds with status 200
    And a YAHOO_OAUTH token item still exists for the default user

  Scenario: Deleting a Sleeper league never removes a Yahoo OAuth token
    Given a YAHOO_OAUTH token item exists for the default user
    When I DELETE "/leagues/100?platform=SLEEPER"
    Then the API responds with status 200
    And a YAHOO_OAUTH token item still exists for the default user

  Scenario: Deleting the owner's last opted-in ESPN league removes their stored cookies
    Given a LEAGUE_LOOKUP exists for league "500" platform "ESPN" canonical "canon-e"
    And an ESPN_CREDENTIALS item exists for the default user
    When I DELETE "/leagues/500?platform=ESPN"
    Then the API responds with status 200
    And no ESPN_CREDENTIALS item exists for the default user

  Scenario: Deleting an ESPN league keeps the cookies when another opted-in ESPN league remains
    Given a LEAGUE_LOOKUP exists for league "500" platform "ESPN" canonical "canon-e"
    And an onboarded ESPN league "canon-e2" opted into auto-refresh owned by the default user
    And an ESPN_CREDENTIALS item exists for the default user
    When I DELETE "/leagues/500?platform=ESPN"
    Then the API responds with status 200
    And an ESPN_CREDENTIALS item still exists for the default user

  Scenario: Deleting a Sleeper league never removes ESPN cookies
    Given an ESPN_CREDENTIALS item exists for the default user
    When I DELETE "/leagues/100?platform=SLEEPER"
    Then the API responds with status 200
    And an ESPN_CREDENTIALS item still exists for the default user
