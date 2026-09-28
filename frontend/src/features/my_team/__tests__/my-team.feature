Feature: My Team page (frontend/my-team)
  A signed-in manager claims their team once and then sees their week at a glance.

  Scenario: First visit shows the picker
    Given the league data is available
    And I have not claimed a team
    When I open My Team
    Then I see the "Which team is yours?" picker listing 4 teams
    And I do not see the Your week card

  Scenario: Save a claim
    Given the league data is available
    And I have not claimed a team
    When I open My Team
    And I pick "Team 1" and save
    Then my claim for "owner-1" was saved
    And I see the Your week card for "Team 1"

  Scenario: Save fails
    Given the league data is available
    And I have not claimed a team
    And saving a claim fails
    When I open My Team
    And I pick "Team 2" and save
    Then I see the error "Failed to save your team."
    And the picker is still shown with "Team 2" selected

  Scenario: Claimed owner absent from the current season
    Given the league data is available
    And I have claimed owner "departed-owner"
    When I open My Team
    Then I see the "Which team is yours?" picker listing 4 teams

  Scenario: Metrics for an in-progress season
    Given the league data is available
    And I have claimed owner "owner-1"
    When I open My Team
    Then the card heading reads "Your week · Week 3"
    And the "Last week" tile shows "W 128.4" and "vs 112.9 · won by 15.5"
    And the "Record" tile shows "2–0" and "1st · 248.40 PF"
    And the "Playoff odds" tile shows the predictor's odds and change
    And the "Lineup efficiency" tile shows "84%" and "12.0 pts left on bench last week"
    And the awards row reads "Last week: Highest Score, Biggest Blowout" and "Highest Score 2× this season"

  Scenario: Matchup with history
    Given the league data is available
    And I have claimed owner "owner-1"
    When I open My Team
    Then the matchup panel shows "Team 4" as the opponent
    And the matchup panel shows "All-time H2H 1–1 (tied)"
    And the matchup panel shows "Last meeting L 100.0–140.0 · 2024 Wk 9"
    And the matchup panel links to the full preview on Matchups

  Scenario: No matchup this week
    Given the league data is available
    And I have claimed owner "owner-1"
    And my team has a bye in Week 3
    When I open My Team
    Then the matchup panel shows "No matchup this week"

  Scenario: Change team
    Given the league data is available
    And I have claimed owner "owner-1"
    When I open My Team
    And I choose "Change team"
    And I pick "Team 2" and save
    Then my claim for "owner-2" was saved
    And I see the Your week card for "Team 2"

  Scenario: Top three draft picks by VORP
    Given the league data is available
    And I have claimed owner "owner-1"
    When I open My Team
    Then my top draft picks are "Player 1, Player 9, Player 5"
    And top pick 1 shows "RB", "Rd 1, Pick 1 (#1)", "+85.2 VORP" and "185.2 pts"

  Scenario: No draft data
    Given the league data is available
    And I have claimed owner "owner-1"
    And the league has no draft data
    When I open My Team
    Then the draft picks section shows "No draft value data yet"
    And the card heading reads "Your week · Week 3"

  Scenario: Draft data fails to load
    Given the league data is available
    And I have claimed owner "owner-1"
    And the draft data fails to load
    When I open My Team
    Then the draft picks section shows "No draft value data yet"
    And the card heading reads "Your week · Week 3"

  Scenario: Week 1
    Given the league data is available
    And I have claimed owner "owner-1"
    And no game of the season has been played
    When I open My Team
    Then the card heading reads "Your week · Week 1"
    And the "Last week" tile shows "—" and "No games played yet"
    And the "Lineup efficiency" tile shows "—" and "Not available yet"
    And the "Playoff odds" tile sub reads "Change not available yet"
    And the win probability is "50% win probability"

  Scenario: Offseason
    Given the league data is available
    And I have claimed owner "owner-1"
    And every matchup of the season has been played
    When I open My Team
    Then the card heading reads "Final result · 2025 season"
    And the "Final standing" tile shows "1st" and "League champion"
    And the "Final record" tile shows "3–0" and "358.40 PF | 312.90 PA"
    And the "Longest win streak" tile shows "3"
    And the "Longest win streak" tile has no subtext
    And the "Lineup efficiency" tile has no subtext

  Scenario: Offseason without a title
    Given the league data is available
    And I have claimed owner "owner-2"
    And every matchup of the season has been played
    When I open My Team
    Then the card heading reads "Final result · 2025 season"
    And the "Final standing" tile has no subtext

  Scenario: Placeholder cannot be toggled
    Given the league data is available
    And I have claimed owner "owner-1"
    When I open My Team
    And I try to toggle "Email me each week"
    Then the "Email me each week" switch is disabled and off
    And "COMING SOON!" is shown
    When I hover the weekly emails info icon
    Then the tooltip describes the "On Tuesday, a recap of last week" and the "are opted out by default"
    And no claim was saved

  Scenario: Loading
    Given the league data is available
    And the league data is slow to load
    When I open My Team
    Then I see the loading skeleton

  Scenario: Claim load fails
    Given the league data is available
    And loading my claim fails
    When I open My Team
    Then I see the error "Failed to load your team."

  Scenario: League data load fails
    Given the league data is available
    And I have claimed owner "owner-1"
    And the league data fails to load
    When I open My Team
    Then I see the error "Failed to load league data."

  Scenario: Demo defaults to a team and does not persist a change
    Given the league data is available
    And demo mode is active
    When I open My Team
    Then I see the Your week card for the demo league's first team
    When I choose "Change team"
    And I pick the demo league's second team and save
    Then I see the Your week card for the demo league's second team
    When I reopen My Team
    Then I see the Your week card for the demo league's first team
