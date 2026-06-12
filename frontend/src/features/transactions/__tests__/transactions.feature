Feature: Transactions (FE-027)
  The transactions page lists a season's completed Sleeper transactions. Trades show
  only what each team received (the other side's drop is redundant); waivers and free
  agents show both the add and the drop. Empty and error states are surfaced inline.

  Scenario: A trade shows only what each team received
    Given transactions data is available
    When I open the transactions page
    Then I see the received player "Run Back"
    And I see the received player "Pat Quarterback"
    And I see the traded pick "2024 Round 2 pick (Tight End)"
    And "Pat Quarterback" is shown only once

  Scenario: A waiver shows both the add and the drop
    Given transactions data is available
    When I open the transactions page
    Then I see the received player "Wide Receiver"
    And I see the received player "Bench Guy"

  Scenario: A season with no transactions shows an empty state
    Given the league has no transactions
    When I open the transactions page
    Then I see the message "No transactions for this season."

  Scenario: A failed load surfaces an inline error
    Given the transactions data fails to load
    When I open the transactions page
    Then I see the message "Failed to load transactions."
