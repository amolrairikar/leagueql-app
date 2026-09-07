Feature: Invite-link redemption (backend/league-authorization / frontend/ownership-transfer)
  Opening an owner-shared invite link joins a signed-in caller to a private ESPN
  league without ESPN cookies. A signed-out caller is asked to sign in first, and
  an invalid or revoked link surfaces an inline error.

  Scenario: A valid invite link joins the league and opens the dashboard
    Given I am signed in
    And the invite token is accepted
    When I open the invite link for ESPN league "100"
    Then I am routed to the home page

  Scenario: A revoked invite link shows an inline error
    Given I am signed in
    And the invite token is rejected as invalid
    When I open the invite link for ESPN league "100"
    Then I see an inline error "This invite link is invalid or has been revoked"

  Scenario: A signed-out caller is prompted to sign in first
    Given I am signed out
    When I open the invite link for ESPN league "100"
    Then I am prompted to sign in
