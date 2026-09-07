Feature: Owner invite link (backend/league-authorization / frontend/ownership-transfer)
  An owner creates a reusable invite link for an ESPN league and shares it with
  leaguemates. Creating a link surfaces a shareable /join URL carrying the minted
  token.

  Scenario: Creating an invite link shows a shareable /join URL
    Given the invite dialog is open for ESPN league "100"
    And the backend mints an invite token "invite-tok-123"
    When I create the invite link
    Then I see a shareable link containing "/join/100?platform=ESPN&invite=invite-tok-123"
    And I see a confirmation that the link was created

  Scenario: Regenerating replaces the link with a new one
    Given the invite dialog is open for ESPN league "100"
    And the backend mints a fresh token on each request
    When I create the invite link
    And I create a new link
    Then I see a shareable link containing "invite=token-2"

  Scenario: Reopening the dialog shows the previously created link
    Given the invite dialog harness is open for ESPN league "100"
    And the backend mints an invite token "persist-tok"
    When I create the invite link
    And I close the dialog and reopen it
    Then I see a shareable link containing "invite=persist-tok"
