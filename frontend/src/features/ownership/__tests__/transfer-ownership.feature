Feature: Transfer ownership dialog (frontend/ownership-transfer)
  The owner mints a one-time transfer token and copies it to share with the new
  owner, with visual confirmation that the copy succeeded.

  Scenario: Generating a token and copying it shows confirmation
    Given the transfer ownership dialog is open
    When I generate a transfer token
    Then I see the token "TOK-123"
    And the copy button reads "Copy"
    When I click the copy button
    Then the token is written to the clipboard
    And the copy button reads "Copied"
