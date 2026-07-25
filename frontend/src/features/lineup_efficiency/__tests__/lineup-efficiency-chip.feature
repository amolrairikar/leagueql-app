Feature: Lineup efficiency chip (FE-034)
  A free chip under each team's name in the box score shows the manager's
  lineup-efficiency %, and opens a slot-by-slot start/sit report.

  Scenario: The chip shows the efficiency % and start/sit report
    When I view the box score chip for a manager who left points on the bench
    Then the chip shows "53% efficient"
    When I open the start/sit report
    Then I see the benched player "WR Stud" listed as the optimal choice

  Scenario: Without bench data no chip is shown
    When I view the box score chip for a season with no bench data
    Then no chip is rendered

  Scenario: A perfect lineup shows full efficiency
    When I view the box score chip for a manager with a perfect lineup
    Then the chip shows "100% efficient"
    When I open the start/sit report
    Then I see "Perfect lineup" in the report
