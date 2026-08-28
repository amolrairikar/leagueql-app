Feature: Transactions (frontend/transactions)
  The transactions page lists a season's completed Sleeper transactions. Trades show
  only what each team received (the other side's drop is redundant); waivers and free
  agents show both the add and the drop. The type filter offers Trades / Waivers / Free
  Agents (no "All") and defaults to Trades. Empty and error states are surfaced inline.

  Scenario: Trades are shown by default with no All option
    Given transactions data is available
    When I open the transactions page
    Then I see the received player "Pat Quarterback"
    And I do not see the player "Wide Receiver"
    And there is no "All" filter option

  Scenario: A trade shows only what each team received
    Given transactions data is available
    When I open the transactions page
    Then I see the received player "Run Back"
    And I see the received player "Pat Quarterback"
    And I see the traded pick "2024 Round 2 pick"
    And "Pat Quarterback" is shown only once

  Scenario: A waiver shows both the add and the drop
    Given transactions data is available
    When I open the transactions page
    And I select the "Waivers" filter
    Then I see the received player "Wide Receiver"
    And I see the received player "Bench Guy"

  Scenario: Selecting Free Agents narrows the wire
    Given transactions data is available
    When I open the transactions page
    And I select the "Free Agents" filter
    Then I see the received player "Free Agent One"
    And I do not see the player "Pat Quarterback"

  Scenario: The summary table breaks down activity per owner
    Given transactions data is available
    When I open the transactions page
    Then the summary row for "Bob" shows waivers "0", free agents "2", trades "1", total "3"
    And the summary row for "Alice" shows waivers "1", free agents "0", trades "1", total "2"
    And owner "Bob" is listed above owner "Alice" in the summary table

  Scenario: The summary reuses each owner's Season Standings avatar and color
    Given transactions and standings data are available
    When I open the transactions page
    Then owner "Bob" shows the standings team logo and standings color

  Scenario: A season with no transactions shows an empty state
    Given the league has no transactions
    When I open the transactions page
    Then I see the message "No transactions for this season."

  Scenario: A failed load surfaces an inline error
    Given the transactions data fails to load
    When I open the transactions page
    Then I see the message "Failed to load transactions."
