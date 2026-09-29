Feature: Integrations nav item (frontend/integrations)
  The sidebar always shows the Community group's Integrations item.

  Scenario: The sidebar shows the Integrations nav item
    When I render the sidebar
    Then I see the "Community" group with an "Integrations" link to "/integrations"
