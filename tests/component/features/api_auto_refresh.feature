Feature: Manage per-league auto-refresh (backend/scheduled-league-auto-refresh)
  PUT /leagues/{id}/auto-refresh sets the auto_refresh_enabled flag on METADATA (owner only),
  and removes the owner's stored ESPN cookies when they opt out of their last ESPN league.

  Scenario: Owner enables auto-refresh for a Yahoo league
    Given a LEAGUE_LOOKUP exists for league "300" platform "YAHOO" canonical "canon-y"
    When I PUT auto-refresh "true" for "/leagues/300/auto-refresh?platform=YAHOO"
    Then the API responds with status 200
    And the METADATA auto_refresh_enabled for league "canon-y" is "true"

  Scenario: Owner disables their last opted-in ESPN league and stored cookies are removed
    Given a LEAGUE_LOOKUP exists for league "500" platform "ESPN" canonical "canon-e"
    And an ESPN_CREDENTIALS item exists for the default user
    When I PUT auto-refresh "false" for "/leagues/500/auto-refresh?platform=ESPN"
    Then the API responds with status 200
    And the METADATA auto_refresh_enabled for league "canon-e" is "false"
    And no ESPN_CREDENTIALS item exists for the default user

  Scenario: Disabling one ESPN league keeps cookies when another opted-in ESPN league remains
    Given a LEAGUE_LOOKUP exists for league "500" platform "ESPN" canonical "canon-e"
    And an onboarded ESPN league "canon-e2" opted into auto-refresh owned by the default user
    And an ESPN_CREDENTIALS item exists for the default user
    When I PUT auto-refresh "false" for "/leagues/500/auto-refresh?platform=ESPN"
    Then the API responds with status 200
    And an ESPN_CREDENTIALS item still exists for the default user
