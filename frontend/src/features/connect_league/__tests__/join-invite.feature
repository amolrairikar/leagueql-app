Feature: Invite-link redemption (backend/league-authorization / frontend/ownership-transfer)
  Opening an owner-shared invite link joins a signed-in caller to a private gated
  league (ESPN or Yahoo) without their own platform credentials. A signed-out
  caller is asked to sign in first, and an invalid, revoked, or Sleeper link
  surfaces an inline error.

  Scenario: A valid invite link joins the league and opens the dashboard
    Given I am signed in
    And the invite token is accepted
    When I open the invite link for ESPN league "100"
    Then I am routed to the home page

  Scenario: A valid Yahoo invite link joins the league and opens the dashboard
    Given I am signed in
    And the invite token is accepted
    When I open the invite link for Yahoo league "100"
    Then I am routed to the home page

  Scenario: A Sleeper invite link is rejected as invalid
    Given I am signed in
    When I open a Sleeper invite link for league "100"
    Then I see an inline error "This invite link is invalid"

  Scenario: A revoked invite link shows an inline error
    Given I am signed in
    And the invite token is rejected as invalid
    When I open the invite link for ESPN league "100"
    Then I see an inline error "This invite link is invalid or has been revoked"

  Scenario: A signed-out caller is prompted to sign in first
    Given I am signed out
    When I open the invite link for ESPN league "100"
    Then I am prompted to sign in
