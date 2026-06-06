Feature: Account menu placement (sign out reachable on mobile)

  The Clerk account / sign-out menu must live outside the modal mobile sidebar
  sheet. Inside the sheet, its portaled dropdown taps fall through to the sidebar
  links beneath and "Sign out" is never clicked (FE-014 / FE-019).

  Scenario: On mobile the account menu is in the header, not the sidebar sheet
    Given I am signed in on a mobile viewport
    Then the account menu is present in the header
    And it is not inside the sidebar sheet when the sheet is opened

  Scenario: On desktop the account menu stays in the sidebar
    Given I am signed in on a desktop viewport
    Then the account menu is shown exactly once
