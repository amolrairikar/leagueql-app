Feature: Connect league onboarding flow (frontend/connect-league)
  The onboarding form validates input, triggers onboarding, polls the job to
  completion, and routes into the app — surfacing the backend failure reason when
  the job fails.

  Scenario: Submitting without a league ID shows a validation error
    Given the connect league form is open
    When I submit the form without a league ID
    Then I see a validation error "League ID is required"

  Scenario: Submitting an ESPN league with a non-4-digit latest season shows a validation error
    Given the connect ESPN league form is open
    When I submit the ESPN form with latest season "24"
    Then I see a validation error "Latest season must be a 4-digit number (e.g. 2026)"

  Scenario: Typing more than 4 digits in the latest season field shows a live validation error
    Given the connect ESPN league form is open
    When I type latest season "20266" into the ESPN form
    Then I see a validation error "Latest season must be a 4-digit number (e.g. 2026)"

  Scenario: A successful onboard polls to completion and routes home
    Given onboarding will complete successfully
    When I onboard Sleeper league "100"
    Then I am routed to the home page

  Scenario: A failed job surfaces the backend failure reason
    Given onboarding will fail with reason "We could not reach Sleeper right now."
    When I onboard Sleeper league "100"
    Then I see a failure message "We could not reach Sleeper right now."

  Scenario: Opening an already-onboarded league as a non-owner routes home without refreshing
    Given the league is already onboarded and I am not its owner
    When I onboard Sleeper league "100"
    Then I am routed to the home page
    And no onboard or refresh request was made

  Scenario: Connecting to an ESPN league I am not yet a member of verifies membership
    Given the ESPN league is onboarded but I am not yet a member
    When I connect ESPN league "100"
    Then I am routed to the home page
    And membership verification was requested
