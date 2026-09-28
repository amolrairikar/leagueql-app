Feature: Integrations route gating (frontend/integrations)
  /integrations renders the Integrations page only while the `integrations`
  feature flag is on; otherwise it redirects to /home.

  Scenario: Flag on renders the page
    Given the "integrations" feature flag is on
    And the integrations endpoint returns no integrations
    When I navigate to "/integrations"
    Then I see the Integrations page

  Scenario: Flag off redirects home
    Given the "integrations" feature flag is off
    When I navigate to "/integrations"
    Then I land on the home page
