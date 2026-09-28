Feature: Submit an integration for review (frontend/integrations)
  A signed-in member submits something they built on the league export. The
  backend opens a review issue; the dialog reports success or explains a failure
  inline without losing what was typed.

  Scenario: Successful submission
    Given the submit dialog is open
    And the submit endpoint will accept the submission as issue 331
    When I fill in a complete "Bot" submission named "Trade Grader"
    And I click "Submit for review"
    Then the dialog shows "Submitted for review" and that the submission was received
    And the submission sent "Trade Grader" with views "transactions,matchups" and no prompt

  Scenario: Submit is disabled until the form is complete
    Given the submit dialog is open
    Then the submit button is disabled
    When I fill in a complete "Bot" submission named "Trade Grader"
    Then the submit button is enabled

  Scenario: Daily limit reached
    Given the submit dialog is open
    And the submit endpoint will reject the submission with status 429 and message "You've reached the limit of 3 integration submissions per day. Try again in 5 hours."
    When I fill in a complete "Bot" submission named "Trade Grader"
    And I click "Submit for review"
    Then the dialog shows the error "You've reached the limit of 3 integration submissions per day. Try again in 5 hours."
    And the name field still reads "Trade Grader"

  Scenario: Server failure
    Given the submit dialog is open
    And the submit endpoint will reject the submission with status 502 and message "Bad Gateway"
    When I fill in a complete "Bot" submission named "Trade Grader"
    And I click "Submit for review"
    Then the dialog shows the error "Couldn't submit right now. Try again in a few minutes."
    And the name field still reads "Trade Grader"

  Scenario: AI prompts are guided to put the prompt in the setup steps
    Given the submit dialog is open
    Then there is no separate prompt field
    And the setup steps hint asks for the prompt
    When I choose the "Bot" category
    Then the setup steps hint does not mention a prompt


  Scenario: Enter starts the next setup step
    Given the submit dialog is open
    When I type a step and press Enter
    Then a second step is added and focused

  Scenario: A pasted multi-line prompt stays one step
    Given the submit dialog is open
    When I paste a multi-line prompt into a step
    Then the step holds the prompt on one line

  Scenario: Steps can be added up to the limit and removed
    Given the submit dialog is open
    Then the only step cannot be removed
    When I add steps until there are 10
    Then no more steps can be added
    When I remove step 3
    And there are 9 steps and the fourth step moved up
