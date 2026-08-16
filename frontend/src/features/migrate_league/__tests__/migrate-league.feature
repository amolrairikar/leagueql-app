Feature: Migrate league flow (FE-003)
  The migration wizard collects the destination platform + league, maps managers,
  submits the migration, and polls the job to completion before routing home.

  Scenario: A migration submits and polls to completion, then routes home
    Given a migration that will complete successfully
    When I complete the migration wizard for ESPN league "777"
    Then I am routed to the home page

  Scenario: A non-4-digit ESPN latest season shows a validation error
    Given a migration that will complete successfully
    When I advance the wizard for ESPN league "777" with latest season "25"
    Then I see a validation error "Latest season must be a 4-digit year"
