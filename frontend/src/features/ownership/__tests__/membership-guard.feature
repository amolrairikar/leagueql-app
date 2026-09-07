Feature: ESPN membership guard (backend/league-authorization / frontend/ownership-transfer)
  ESPN league reads are member-gated. A non-member (a 403) is shown guidance to
  obtain an invite link from the league owner instead of the dashboard; a member
  (a 200) sees the gated content.

  Scenario: A non-member is directed to an invite link
    Given the ESPN league returns 403 for the current caller
    When I open the ESPN league behind the membership guard
    Then I see the guidance "Ask the league owner to share their invite link"
    And I do not see the gated content "Protected dashboard"

  Scenario: A member sees the gated content
    Given the ESPN league returns 200 for the current caller
    When I open the ESPN league behind the membership guard
    Then I see the gated content "Protected dashboard"
