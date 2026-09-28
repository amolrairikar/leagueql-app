Feature: Community integrations backed by GitHub issues (backend/integrations)
  POST /integrations opens a review issue in the LeagueQL repo and GET /integrations lists the
  issues the maintainer approved. GitHub is replaced by an in-memory fake; DynamoDB (the
  per-user submission limit) is real moto.

  Background:
    Given GitHub is reachable

  Scenario: A submission is listed only after the maintainer approves it
    Given the "integrations" feature flag is on
    When I submit the integration "Trade Grader"
    Then the API responds with status 201
    And GitHub has an issue titled "[Integration] Trade Grader" labeled "integration:submitted"
    When I GET "/integrations"
    Then the API responds with status 200
    And the integrations listing has 0 item(s)
    When the maintainer adds the "integration:approved" label to "[Integration] Trade Grader"
    And the integrations listing cache has expired
    And I GET "/integrations"
    Then the integrations listing has 1 item(s)
    And the integrations listing includes "Trade Grader" by "benchwarmer"

  Scenario: The newest featured integration is the only featured one
    Given the "integrations" feature flag is on
    And GitHub has an approved integration "Older" labeled "integration:featured"
    And GitHub has an approved integration "Newer" labeled "integration:featured"
    When I GET "/integrations"
    Then the integrations listing has 2 item(s)
    And only "Newer" is featured in the integrations listing

  Scenario: A fourth submission within a day is rejected
    Given the "integrations" feature flag is on
    When I submit the integration "One"
    And I submit the integration "Two"
    And I submit the integration "Three"
    And I submit the integration "Four"
    Then the API responds with status 429
    And the API response detail contains "limit of 3"
    And GitHub has 3 issue(s)
    And the default user has 3 recorded integration submission(s)

  Scenario: A GitHub failure returns 502 and does not count toward the limit
    Given the "integrations" feature flag is on
    And GitHub rejects issue creation
    When I submit the integration "Trade Grader"
    Then the API responds with status 502
    And the API response detail is "Couldn't submit right now. Try again in a few minutes."
    And the default user has 0 recorded integration submission(s)

  Scenario: The endpoints are hidden while the flag is off
    When I submit the integration "Trade Grader"
    Then the API responds with status 404
    And GitHub has 0 issue(s)
    When I GET "/integrations"
    Then the API responds with status 404
