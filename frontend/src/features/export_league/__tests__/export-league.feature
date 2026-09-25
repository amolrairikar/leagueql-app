Feature: Export league data dialog (frontend/export-league-data)
  A league member picks which seasons to export and downloads the league's
  processed data as a ZIP of one JSON file per view per season.

  Scenario: Season checkboxes render and export is disabled until a season is picked
    Given the export dialog is open for a league with seasons "2022,2023,2024"
    Then I see a checkbox for each season
    And the export button is disabled

  Scenario: Selecting all seasons and exporting downloads a ZIP
    Given the export dialog is open for a league with seasons "2023,2024"
    When I select all seasons
    And I click export
    Then the league data is downloaded as a ZIP
    And the export was requested for seasons "2023,2024"

  Scenario: An export failure shows an inline error
    Given the export dialog is open for a league with seasons "2024"
    And the export endpoint will fail
    When I select season "2024"
    And I click export
    Then I see an inline export error
    And no file is downloaded
