Feature: Owner invite link (backend/league-authorization / frontend/ownership-transfer)
  An owner creates a reusable invite link for an ESPN league and shares it with
  leaguemates. Creating a link surfaces a shareable /join URL carrying the minted
  token.

  Scenario: Creating an invite link shows a shareable /join URL
    Given the invite dialog is open for ESPN league "100"
    And the backend mints an invite token "invite-tok-123"
    When I create the invite link
    Then I see a shareable link containing "/join/100?platform=ESPN&invite=invite-tok-123"
