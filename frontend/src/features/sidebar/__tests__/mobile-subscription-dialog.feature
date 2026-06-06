Feature: Manage Subscription dialog on mobile

  On mobile the sidebar is a slide-over sheet. Selecting "Manage Subscription"
  closes that sheet, but the dialog must stay open — it is rendered outside the
  sheet subtree so closing the sheet does not unmount it (FE-023).

  Scenario: The dialog stays open after the mobile sidebar closes
    Given I am on a mobile viewport with an active subscription
    When I open the sidebar and select Manage Subscription
    Then the Manage Subscription dialog is open
    And the sidebar sheet has closed
