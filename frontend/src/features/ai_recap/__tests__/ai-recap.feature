Feature: AI weekly recap (FE-033)
  The matchups page hosts a premium AI weekly recap section below the weekly awards:
  a headline and narrative recap for the selected season/week, fetched from the RECAP
  view. It is gated behind the premium_feature flag.

  Scenario: A generated recap renders its headline and body
    Given a recap exists for the selected week
    When I open the AI recap
    Then I see the recap headline "Week 1: Alice Runs the Table"
    And I see the recap body text "Alice steamrolled the league this week."

  Scenario: A week with no recap yet shows an empty state
    Given no recap has been generated for the selected week
    When I open the AI recap
    Then I see "No recap for this week yet. Recaps are generated automatically — check back shortly."

  Scenario: A failed load surfaces an inline message
    Given the recap data fails to load
    When I open the AI recap
    Then I see "Failed to load the weekly recap."

  Scenario: An expired subscription shows the locked overlay without fetching data
    Given the premium_feature flag is on and the league subscription has expired
    When I open the gated AI recap
    Then I see the paywall heading "AI weekly recap is a premium feature"
    And the AI recap is not rendered
