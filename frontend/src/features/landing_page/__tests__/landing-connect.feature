Feature: Landing page connect routing (frontend/landing-page / frontend/connect-league / frontend/ownership-transfer)
  Connecting from the landing page routes ESPN leagues that need onboarding to the
  connect form, and opens the Join League dialog for leagues the caller isn't a
  member of yet.

  Scenario: Connecting an ESPN league I am not a member of opens the Join dialog
    Given the ESPN league read is member-gated for me
    When I submit an ESPN league ID from the landing page
    Then I see the "Join league" dialog
    When I verify my ESPN membership in the dialog
    Then I am routed to the home page
