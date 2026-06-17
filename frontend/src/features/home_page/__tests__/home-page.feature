Feature: Home dashboard (FE-004)
  The dashboard derives every section from one league-data request, surfaces a
  single inline error on failure, and renders empty states for a league with no
  games yet.

  Scenario: The dashboard renders stats, champions and standings when data loads
    Given a connected league with home dashboard data
    When I open the home dashboard
    Then I see the league name "My League"
    And I see the headline stat "Total matchups"
    And I see the champion manager "Alice"

  Scenario: A failed data load shows a single inline error
    Given a connected league whose data fails to load
    When I open the home dashboard
    Then I see an inline error "Failed to load league data."

  Scenario: A league with no games shows an empty standings state
    Given a connected league with no games yet
    When I open the home dashboard
    Then I see "No standings data available."

  Scenario: The dashboard renders without crashing when seasons cookie has expired
    Given a connected league with no seasons
    When I open the home dashboard
    Then I see the headline stat "Total matchups"
