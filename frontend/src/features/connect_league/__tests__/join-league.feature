Feature: Join League dialog (frontend/connect-league / frontend/ownership-transfer)
  A non-member joins a private ESPN league by verifying their ESPN cookies. The
  dialog only verifies membership — it never onboards or refreshes the league.

  Scenario: Autofilled cookies that ESPN rejects show an inline error
    Given the Join League dialog is open for an ESPN league
    And the extension supplies ESPN cookies
    And ESPN will reject the cookies
    When I autofill my cookies and try to join
    Then I see an inline error "We couldn't confirm you're in this ESPN league."

  Scenario: Without the extension, an install link is shown instead of the autofill button
    Given the Join League dialog is open without the extension installed
    Then there is no autofill button
    And I see a link to install the LeagueQL ESPN Cookie Helper extension
