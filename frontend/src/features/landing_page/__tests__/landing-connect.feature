Feature: Landing page connect routing (frontend/landing-page / frontend/connect-league / frontend/ownership-transfer / frontend/connect-yahoo-league)
  Connecting from the landing page routes ESPN leagues that need onboarding to the
  connect form, and directs the caller to an owner's invite link for a private
  league they aren't a member of yet. A Yahoo league is onboarded in place when the
  caller is already linked; only an unlinked (or revoked) caller is sent to Yahoo's
  consent screen.

  Scenario: Connecting an ESPN league I am not a member of shows invite-link guidance
    Given the ESPN league read is member-gated for me
    When I submit an ESPN league ID from the landing page
    Then I see invite-link guidance "Ask the league owner to share their invite link"

  Scenario: The connect form offers Yahoo as a selectable platform
    Given the landing connect form is open
    When I open the platform dropdown
    Then Yahoo is offered as a selectable platform

  Scenario: Connecting a Yahoo league I have not linked starts the OAuth flow
    Given onboarding a Yahoo league is rejected as unlinked and the authorize endpoint returns a consent URL
    When I connect a Yahoo league "45.l.678" from the landing page
    Then the Yahoo authorization is requested for that league

  Scenario: Connecting a Yahoo league I have already linked onboards in place
    Given onboarding a linked Yahoo league completes successfully
    When I connect a Yahoo league "45.l.678" from the landing page
    Then I land on the league home page

  Scenario: Connecting an already-onboarded Yahoo league routes straight in
    Given the Yahoo league is already onboarded
    When I connect a Yahoo league "45.l.678" from the landing page
    Then I land on the league home page

  Scenario: A revoked Yahoo link restarts the OAuth flow
    Given onboarding a linked Yahoo league fails with a re-link signal and the authorize endpoint returns a consent URL
    When I connect a Yahoo league "45.l.678" from the landing page
    Then the Yahoo authorization is requested for that league

  Scenario: Enabling auto-refresh when connecting a linked Yahoo league sends the opt-in
    Given onboarding a linked Yahoo league completes successfully
    When I connect a Yahoo league "45.l.678" with auto-refresh enabled
    Then the Yahoo onboard request included auto-refresh
