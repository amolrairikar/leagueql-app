Feature: Landing page connect routing (frontend/landing-page / frontend/connect-league / frontend/ownership-transfer)
  Connecting from the landing page routes ESPN leagues that need onboarding to the
  connect form, and directs the caller to an owner's invite link for a private
  league they aren't a member of yet.

  Scenario: Connecting an ESPN league I am not a member of shows invite-link guidance
    Given the ESPN league read is member-gated for me
    When I submit an ESPN league ID from the landing page
    Then I see invite-link guidance "Ask the league owner to share their invite link"

  Scenario: The connect form offers Yahoo as a selectable platform
    Given the landing connect form is open
    When I open the platform dropdown
    Then Yahoo is offered as a selectable platform

  Scenario: Connecting a Yahoo league starts the OAuth flow
    Given the Yahoo authorize endpoint returns a consent URL
    When I connect a Yahoo league "45.l.678" from the landing page
    Then the Yahoo authorization is requested for that league
