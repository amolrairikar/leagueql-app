Feature: Integrations nav gating (frontend/integrations)
  The Community group's Integrations item is shown only while the
  `integrations` feature flag is on.

  Scenario: Flag on shows the Integrations nav item
    Given the "integrations" feature flag is on
    When I render the sidebar
    Then I see the "Community" group with an "Integrations" link to "/integrations"

  Scenario: Flag off hides the Integrations nav item
    Given the "integrations" feature flag is off
    When I render the sidebar
    Then I do not see an "Integrations" nav item
