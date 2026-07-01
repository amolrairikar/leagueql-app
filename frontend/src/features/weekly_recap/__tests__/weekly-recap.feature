Feature: Weekly matchup recap (FE-037)
  The matchups page hosts a premium weekly-recap section: an AI-written recap
  column (headline + body paragraphs) for the selected week, read from the cached
  MATCHUP_RECAP view. It is gated behind the premium_feature flag.

  Scenario: The recap renders for a week with a cached recap
    Given a cached recap is available for the season
    When I open the weekly recap
    Then I see "Week 1: Fireworks and Faceplants"
    And I see "Alice torched the scoreboard."

  Scenario: Copying a recap writes it to the clipboard and shows a check mark
    Given a cached recap is available for the season
    When I open the weekly recap
    And I click the copy recap button
    Then the recap headline and body are written to the clipboard
    And the copy button shows it has copied

  Scenario: A week with no cached recap shows the generating message
    Given the week has no cached recap
    When I open the weekly recap
    Then I see "Weekly recap generating! Check back soon."

  Scenario: A failed load surfaces an inline message
    Given the recap data fails to load
    When I open the weekly recap
    Then I see "Failed to load weekly recap."

  Scenario: An expired subscription shows the locked overlay without fetching data
    Given the premium_feature flag is on and the league subscription has expired
    When I open the gated weekly recap
    Then I see the paywall heading "Weekly matchup recap is a premium feature"
    And the recap is not rendered
