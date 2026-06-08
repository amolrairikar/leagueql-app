Feature: Billing sections in the user guide are feature-flagged (FE-026)
  The /docs user guide shows subscription/billing guidance only when billing is
  enabled; with billing off those sections (and their TOC entries) are hidden.

  Scenario: Billing enabled shows the subscription sections
    Given billing is enabled
    When I open the user guide
    Then I see the "Subscribing" guide section
    And I see the "Managing Billing" guide section
    And I see the "Free Trial" guide section

  Scenario: Billing disabled hides the subscription sections
    Given billing is disabled
    When I open the user guide
    Then I see the "Refresh League" guide section
    And I do not see the "Subscribing" guide section
    And I do not see the "Managing Billing" guide section
    And I do not see the "Free Trial" guide section
