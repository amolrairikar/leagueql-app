Feature: Lineup efficiency chip (FE-034)
  A premium chip under each team's name in the box score shows the manager's
  lineup-efficiency %, and opens a slot-by-slot start/sit report. It is gated
  behind the premium_feature flag.

  Scenario: An active subscription shows the chip and start/sit report
    Given the premium_feature flag is on and the league subscription is active
    When I view the box score chip for a manager who left points on the bench
    Then the chip shows "53% efficient"
    When I open the start/sit report
    Then I see the benched player "WR Stud" listed as the optimal choice

  Scenario: An expired subscription locks the chip behind the paywall
    Given the premium_feature flag is on and the league subscription has expired
    When I view the box score chip for a manager who left points on the bench
    Then the chip shows "Lineup efficiency" without an efficiency percentage
    When I open the start/sit report
    Then I see the paywall heading "Lineup efficiency is a premium feature"
    And the benched player "WR Stud" is not shown

  Scenario: Without the premium flag the chip is free
    Given the premium_feature flag is off
    When I view the box score chip for a manager who left points on the bench
    Then the chip shows "53% efficient"
    When I open the start/sit report
    Then I see the benched player "WR Stud" listed as the optimal choice

  Scenario: With billing disabled no chip is shown
    Given the billing flag is off
    When I view the box score chip for a manager who left points on the bench
    Then no chip is rendered

  Scenario: Without bench data no chip is shown
    Given the premium_feature flag is on and the league subscription is active
    When I view the box score chip for a season with no bench data
    Then no chip is rendered

  Scenario: Demo mode unlocks the chip with a premium hint
    Given the app is in demo mode
    When I view the box score chip for a manager who left points on the bench
    Then the chip shows "53% efficient"
    When I open the start/sit report
    Then I see the "Premium" hint

  Scenario: A perfect lineup shows full efficiency
    Given the premium_feature flag is on and the league subscription is active
    When I view the box score chip for a manager with a perfect lineup
    Then the chip shows "100% efficient"
    When I open the start/sit report
    Then I see "Perfect lineup" in the report
