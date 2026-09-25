## Purpose

Let a league member choose which seasons to export and download the league's processed data to
their browser as a ZIP of per-view-per-season JSON files.

## ADDED Requirements

### Requirement: Season selection dialog
The export action SHALL open a dialog listing a checkbox for each of the league's onboarded seasons
plus a "Select all" control that toggles every season at once. The confirm/export button SHALL be
disabled until at least one season is selected.

#### Scenario: Seasons listed
- **WHEN** the export dialog opens for a connected league
- **THEN** it shows one checkbox per onboarded season and a "Select all" control

#### Scenario: Export disabled with no selection
- **WHEN** no season is selected
- **THEN** the export/confirm button is disabled

#### Scenario: Select all toggles every season
- **WHEN** the user activates "Select all"
- **THEN** every season checkbox becomes checked, and deactivating it clears them

### Requirement: Download selected seasons as a ZIP of JSON files
On confirm, the frontend SHALL request the export for the selected seasons and download the result
to the browser as a single ZIP file containing one JSON file per view per season (named
`<season>_<view>.json`). A loading indicator SHALL be shown while the export is in progress.

#### Scenario: Successful export downloads a ZIP
- **WHEN** the user selects one or more seasons and confirms, and the request succeeds
- **THEN** a ZIP file is downloaded containing one JSON file per view per selected season

#### Scenario: Loading state during export
- **WHEN** an export request is in flight
- **THEN** the dialog shows a loading indicator and the confirm button is disabled

### Requirement: Surface export errors inline
When the export request fails, the dialog SHALL surface the error inline (via the shared error
alert) and remain open so the user can retry, rather than downloading a file.

#### Scenario: Export failure shows inline error
- **WHEN** the export request returns an error
- **THEN** the dialog shows an inline error message, stays open, and no file is downloaded
