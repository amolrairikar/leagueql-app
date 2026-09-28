Feature: Integrations page (frontend/integrations)
  League members browse maintainer-approved integrations built on the league
  export, filter and search them, and open one to see how to set it up.

  Scenario: Approved integrations render with the featured one highlighted
    Given the integrations endpoint returns three integrations with "League Historian" featured
    When I open the integrations page
    Then I see the page heading and the three how-it-works steps
    And the featured card shows "League Historian"
    And the grid shows 3 integration cards

  Scenario: No featured integration
    Given the integrations endpoint returns integrations with none featured
    When I open the integrations page
    Then no featured card is shown
    And the grid shows 2 integration cards

  Scenario: No integrations yet
    Given the integrations endpoint returns no integrations
    When I open the integrations page
    Then I see the empty state inviting a first submission

  Scenario: Listing fails
    Given the integrations endpoint fails with a server error
    When I open the integrations page
    Then I see an inline error about loading integrations
    And the submit button is still available

  Scenario: Filter by category
    Given the integrations endpoint returns three integrations with "League Historian" featured
    When I open the integrations page
    And I select the "Bots" category
    Then the grid shows only "Weekly Recap Bot"
    And the result count reads "1 of 3 integrations"

  Scenario: Search by view name
    Given the integrations endpoint returns three integrations with "League Historian" featured
    When I open the integrations page
    And I search for "transactions"
    Then the grid shows only "League Historian"

  Scenario: No matches
    Given the integrations endpoint returns three integrations with "League Historian" featured
    When I open the integrations page
    And I search for "nothing matches this"
    Then I see the no-matches message

  Scenario: Open integration details
    Given the integrations endpoint returns three integrations with "League Historian" featured
    When I open the integrations page
    And I open the "Weekly Recap Bot" card
    Then the detail dialog shows the setup steps and files for "Weekly Recap Bot"
    And the detail dialog links to "https://github.com/example/recap-bot"
    And the detail dialog has no prompt section

  Scenario: Copy an integration's prompt
    Given the integrations endpoint returns three integrations with "League Historian" featured
    When I open the integrations page
    And I click "View setup" on the featured card
    And I click "Copy prompt"
    Then the prompt is copied to the clipboard
    And the copy button reads "Copied"
