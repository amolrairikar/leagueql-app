Feature: Migrate league flow (FE-003)
  The migration wizard collects the destination platform + league, maps managers,
  submits the migration, and polls the job to completion before routing home.
  Migration is a free feature (not subscription-gated).

  Scenario: A migration submits and polls to completion, then routes home
    Given a migration that will complete successfully
    When I complete the migration wizard for ESPN league "777"
    Then I am routed to the home page
