Feature: Join League dialog (FE-002 / FE-025)
  A non-member joins a private ESPN league by verifying their ESPN cookies. The
  dialog only verifies membership — it never onboards or refreshes the league.

  Scenario: Autofilled cookies that ESPN rejects show an inline error
    Given the Join League dialog is open for an ESPN league
    And the extension supplies ESPN cookies
    And ESPN will reject the cookies
    When I autofill my cookies and try to join
    Then I see an inline error "We couldn't confirm you're in this ESPN league."
