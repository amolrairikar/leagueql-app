Feature: Yahoo OAuth return (frontend/connect-yahoo-league)
  After linking a Yahoo account, the browser returns to the connect page. A successful link
  resumes onboarding and polls the job to completion (the same flow as ESPN/Sleeper); a lost link
  or a YAHOO_AUTH job failure prompts a reconnect, and a cancelled link offers a retry.

  Scenario: A successful Yahoo link onboards and lands on the dashboard
    Given onboarding a Yahoo league completes successfully
    When I return from Yahoo with a linked account for league "678"
    Then I see "HOME PAGE"

  Scenario: A revoked Yahoo token during onboarding prompts a reconnect
    Given onboarding a Yahoo league fails with a re-link signal
    When I return from Yahoo with a linked account for league "678"
    Then I see "Reconnect your Yahoo account"

  Scenario: A lost Yahoo link prompts a reconnect
    Given onboarding a Yahoo league is rejected as unlinked
    When I return from Yahoo with a linked account for league "678"
    Then I see "Reconnect your Yahoo account"

  Scenario: A cancelled Yahoo link offers a retry
    When I return from Yahoo with a cancelled link
    Then I see "Yahoo linking was cancelled or failed"
    And I see a "Connect with Yahoo" button
