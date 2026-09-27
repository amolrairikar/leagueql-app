Feature: Landing page connect routing (frontend/landing-page / frontend/connect-league / frontend/ownership-transfer / frontend/connect-yahoo-league)
  Connecting from the landing page routes ESPN leagues that need onboarding to the
  connect form, and directs the caller to an owner's invite link for a private
  league they aren't a member of yet. A Yahoo league is onboarded in place when the
  caller is already linked; only an unlinked (or revoked) caller is sent to Yahoo's
  consent screen.

  Scenario: ESPN credential fields stay hidden until the league is looked up
    Given the landing connect form is open with ESPN selected
    Then the ESPN credential fields are not shown
    And the "League not added to LeagueQL yet" message is not shown

  Scenario: A first Connect on a not-yet-onboarded ESPN league reveals the credential fields
    Given a not-yet-onboarded ESPN league
    When I look up an ESPN league "100" from the landing page
    Then the ESPN credential fields are shown
    And the "League not added to LeagueQL yet" message is shown
    And no ESPN onboard request was made

  Scenario: Connecting an ESPN league I am not a member of shows already-onboarded guidance
    Given the ESPN league read is member-gated for me
    When I submit an ESPN league ID from the landing page
    Then I see invite-link guidance "reach out to your leaguemate who onboarded the league"

  Scenario: Connecting a not-yet-onboarded ESPN league onboards in place
    Given a not-yet-onboarded ESPN league that will onboard successfully and the current season is "2026"
    When I connect an ESPN league "100" with cookies from the landing page
    Then I land on the league home page
    And the ESPN onboard request carried season "2026"

  Scenario: The auto-derived season falls back to the clock when Sleeper is unavailable
    Given a not-yet-onboarded ESPN league that will onboard successfully and the Sleeper season endpoint is unavailable
    When I connect an ESPN league "100" with cookies from the landing page
    Then I land on the league home page
    And the ESPN onboard request carried a 4-digit season

  Scenario: Connecting a not-yet-onboarded ESPN league without cookies shows an inline error
    Given a not-yet-onboarded ESPN league
    When I connect an ESPN league "100" without cookies from the landing page
    Then I see invite-link guidance "Enter your SWID and espn_s2"
    And no ESPN onboard request was made

  Scenario: The connect form offers Yahoo as a selectable platform
    Given the landing connect form is open
    When I open the platform dropdown
    Then Yahoo is offered as a selectable platform

  Scenario: Connecting a Yahoo league I have not linked opens the consent popup
    Given onboarding a Yahoo league is rejected as unlinked and the authorize endpoint returns a consent URL
    When I connect a Yahoo league "45.l.678" from the landing page
    Then the Yahoo consent popup is opened for that league

  Scenario: Linking completes in the popup and resumes onboarding inline
    Given a Yahoo league that is unlinked until the popup links it, then onboards successfully
    When I connect a Yahoo league "45.l.678" and the popup reports a successful link
    Then I land on the league home page

  Scenario: A blocked consent popup falls back to a full-page redirect
    Given onboarding a Yahoo league is rejected as unlinked and the authorize endpoint returns a consent URL
    When I connect a Yahoo league "45.l.678" but the browser blocks the popup
    Then the browser is redirected to the Yahoo consent URL

  Scenario: Dismissing the consent popup shows a retry
    Given onboarding a Yahoo league is rejected as unlinked and the authorize endpoint returns a consent URL
    When I connect a Yahoo league "45.l.678" and then dismiss the popup
    Then I see an inline alert "Yahoo linking was cancelled"

  Scenario: Connecting a Yahoo league I have already linked onboards in place
    Given onboarding a linked Yahoo league completes successfully
    When I connect a Yahoo league "45.l.678" from the landing page
    Then I land on the league home page

  Scenario: Connecting an already-onboarded Yahoo league routes straight in
    Given the Yahoo league is already onboarded
    When I connect a Yahoo league "45.l.678" from the landing page
    Then I land on the league home page

  Scenario: A revoked Yahoo link reopens the consent popup
    Given onboarding a linked Yahoo league fails with a re-link signal and the authorize endpoint returns a consent URL
    When I connect a Yahoo league "45.l.678" from the landing page
    Then the Yahoo consent popup is opened for that league

  Scenario: Enabling auto-refresh when connecting a linked Yahoo league sends the opt-in
    Given onboarding a linked Yahoo league completes successfully
    When I connect a Yahoo league "45.l.678" with auto-refresh enabled
    Then the Yahoo onboard request included auto-refresh

  Scenario: Returning from Yahoo with a linked account resumes onboarding inline
    Given onboarding a linked Yahoo league completes successfully
    When I return from Yahoo to the landing page with a linked account for league "45.l.678"
    Then I land on the league home page

  Scenario: Returning from Yahoo for an already-onboarded league routes straight in
    Given the Yahoo league is already onboarded
    When I return from Yahoo to the landing page with a linked account for league "45.l.678"
    Then I land on the league home page

  Scenario: The auto-refresh opt-in chosen before the redirect is applied on return
    Given onboarding a linked Yahoo league completes successfully
    And the Yahoo auto-refresh opt-in was stashed before the redirect
    When I return from Yahoo to the landing page with a linked account for league "45.l.678"
    Then the Yahoo onboard request included auto-refresh

  Scenario: A revoked Yahoo link surfaced on return reopens the consent popup
    Given onboarding a linked Yahoo league fails with a re-link signal and the authorize endpoint returns a consent URL
    When I return from Yahoo to the landing page with a linked account for league "45.l.678"
    Then the Yahoo consent popup is opened for that league

  Scenario: A cancelled Yahoo link on return shows an inline retry alert
    When I return from Yahoo to the landing page with a cancelled link
    Then I see an inline alert "Yahoo linking was cancelled or failed"
