Feature: Migrate league flow (frontend/migrate-league)
  The migration wizard collects the destination platform + league, maps managers,
  submits the migration, and polls the job to completion before routing home.

  Scenario: A migration submits and polls to completion, then routes home
    Given a migration that will complete successfully
    When I complete the migration wizard for ESPN league "777"
    Then I am routed to the home page

  Scenario: A non-4-digit ESPN latest season shows a live validation error
    Given a migration that will complete successfully
    When I type latest season "20255" for ESPN league "777"
    Then I see a validation error "Latest season must be a 4-digit number (e.g. 2026)"

  Scenario: A linked Yahoo destination fetches members via the proxy and completes
    Given a Yahoo migration where the account is already linked
    When I complete the migration wizard for Yahoo league "999"
    Then I am routed to the home page

  Scenario: An unlinked Yahoo destination prompts the Yahoo OAuth link
    Given a Yahoo migration where the account is not linked
    When I choose Yahoo league "999" as the destination
    Then the Yahoo authorization is requested for migration and the browser is redirected

  Scenario: Returning from Yahoo OAuth resumes the manager-mapping step
    Given a Yahoo migration where the account is already linked
    When I return from Yahoo linking for destination league "999"
    Then I see the manager mapping step
