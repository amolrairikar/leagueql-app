Feature: AI weekly recap backfill (BE-022)
  A genuine premium activation in the Stripe webhook fans out an async AI-recap
  backfill that generates one RECAP item per season/week of MATCHUPS, idempotently.
  The Bedrock LLM call is mocked; real DynamoDB runs via moto. Generated recaps are
  served back through the BE-005 query endpoint.

  Background:
    Given a LEAGUE_LOOKUP exists for league "100" platform "SLEEPER" canonical "canon-1"

  Scenario: Activation backfills a recap for every week of matchups
    Given a subscribable league "canon-1" native "100" on "SLEEPER"
    And league "canon-1" has a "MATCHUPS#2024#WEEK#01" view with 2 row(s)
    And league "canon-1" has a "MATCHUPS#2024#WEEK#02" view with 2 row(s)
    When Stripe sends a "checkout.session.completed" webhook (event "evt_1") for subscription "sub_1" with status "active"
    Then the webhook responds with status 200
    And a RECAP item exists for league "canon-1" season "2024" week "01"
    And a RECAP item exists for league "canon-1" season "2024" week "02"

  Scenario: Re-firing the backfill does not regenerate existing recaps
    Given a subscribable league "canon-1" native "100" on "SLEEPER"
    And league "canon-1" has a "MATCHUPS#2024#WEEK#01" view with 2 row(s)
    When Stripe sends a "checkout.session.completed" webhook (event "evt_1") for subscription "sub_1" with status "active"
    Then the webhook responds with status 200
    And the Bedrock client was called 1 time(s)
    When Stripe sends a "invoice.paid" webhook (event "evt_2") for subscription "sub_1" with status "active"
    Then the webhook responds with status 200
    And the Bedrock client was called 1 time(s)

  Scenario: A generated recap is served through the query endpoint
    Given a subscribable league "canon-1" native "100" on "SLEEPER"
    And league "canon-1" has a "MATCHUPS#2024#WEEK#01" view with 2 row(s)
    When Stripe sends a "checkout.session.completed" webhook (event "evt_1") for subscription "sub_1" with status "active"
    Then the webhook responds with status 200
    When I GET "/leagues/100/query?platform=SLEEPER&queryType=RECAP#2024#WEEK#01"
    Then the API responds with status 200
    And the recap response headline is "Test Headline"
