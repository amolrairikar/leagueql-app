Feature: Yahoo OAuth return (frontend/connect-yahoo-league)
  After linking a Yahoo account, the browser returns to the connect page. A successful link
  resumes onboarding (which surfaces a "coming soon" notice while the Yahoo data client is
  unshipped); a lost link prompts a reconnect, and a cancelled link offers a retry.

  Scenario: A successful Yahoo link shows the coming-soon notice
    Given onboarding a Yahoo league returns the coming-soon signal
    When I return from Yahoo with a linked account for league "45.l.678"
    Then I see "Yahoo account connected"
    And I see "coming soon"

  Scenario: A lost Yahoo link prompts a reconnect
    Given onboarding a Yahoo league is rejected as unlinked
    When I return from Yahoo with a linked account for league "45.l.678"
    Then I see "Reconnect your Yahoo account"

  Scenario: A cancelled Yahoo link offers a retry
    When I return from Yahoo with a cancelled link
    Then I see "Yahoo linking was cancelled or failed"
    And I see a "Connect with Yahoo" button
