Feature: Turn off ESPN auto-refresh from the sidebar (frontend/navigation-sidebar)
  The owner of an ESPN league enrolled in scheduled auto-refresh can turn it off
  from a confirmation dialog, which calls PUT /leagues/{id}/auto-refresh with
  enabled=false. On success the app reloads so the manual Refresh League action
  returns; a failure surfaces an inline error and keeps the dialog open.

  Scenario: Confirming turns auto-refresh off
    Given I own an ESPN league enrolled in auto-refresh
    When I confirm turning auto-refresh off
    Then the app sends a disable request with enabled false
    And the page reloads

  Scenario: Cancelling sends no request
    Given I own an ESPN league enrolled in auto-refresh
    When I cancel the turn-off dialog
    Then no disable request is sent

  Scenario: A failed disable shows an error and keeps the dialog open
    Given turning auto-refresh off will fail
    When I confirm turning auto-refresh off
    Then I see an inline error and the dialog stays open
    And the page does not reload
