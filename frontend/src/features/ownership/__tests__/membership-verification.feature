Feature: ESPN membership verification (LQL-01 / BE-016 / FE-025)
  ESPN league reads are member-gated. A non-member is shown a verification prompt
  and joins through the shared Join League dialog; verifying their ESPN cookies
  unlocks the league, and rejected cookies surface an inline error.

  Scenario: A non-member verifies and unlocks the dashboard
    Given the ESPN league returns 403 for the current caller
    And the extension can supply valid ESPN cookies
    When I open the ESPN league behind the membership guard
    Then I see the verification prompt "Verify your ESPN league membership"
    When verification succeeds
    And I autofill my cookies and join in the dialog
    Then I see the gated content "Protected dashboard"

  Scenario: Rejected cookies show an inline error
    Given the ESPN league returns 403 for the current caller
    And the extension can supply valid ESPN cookies
    When I open the ESPN league behind the membership guard
    Then I see the verification prompt "Verify your ESPN league membership"
    When verification is rejected by ESPN
    And I autofill my cookies and join in the dialog
    Then I see an inline error "We couldn't confirm you're in this ESPN league."
