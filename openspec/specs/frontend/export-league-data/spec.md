# export-league-data Specification

## Purpose

Let a league member choose which seasons to export and download the league's processed data to
their browser as a ZIP of per-view-per-season JSON files.

## Requirements

### Requirement: Season selection dialog
The export action SHALL open a dialog listing a checkbox for each of the league's onboarded seasons
plus an "Export all seasons" control that toggles every season at once. The confirm/export button SHALL be
disabled until at least one season is selected.

#### Scenario: Seasons listed
- **WHEN** the export dialog opens for a connected league
- **THEN** it shows one checkbox per onboarded season and an "Export all seasons" control

#### Scenario: Export disabled with no selection
- **WHEN** no season is selected
- **THEN** the export/confirm button is disabled

#### Scenario: Export all seasons toggles every season
- **WHEN** the user activates "Export all seasons"
- **THEN** every season checkbox becomes checked, and deactivating it clears them

### Requirement: Download selected seasons as a ZIP of JSON files
On confirm, the frontend SHALL request the export for each selected season in its own request, merge
the per-season results, and download them to the browser as a single ZIP file containing one JSON
file per view per season (named `<season>_<view>.json`), plus a `README.md` data guide and a
`manifest.json` at the ZIP root. A season for which the API reports no data SHALL be omitted from
the ZIP. A loading indicator SHALL be shown while the export is in progress.

#### Scenario: Successful export downloads a ZIP
- **WHEN** the user selects one or more seasons and confirms, and every request succeeds
- **THEN** a ZIP file is downloaded containing one JSON file per view per selected season, a
  `README.md`, and a `manifest.json`

#### Scenario: One request per selected season
- **WHEN** the user selects seasons 2023 and 2024 and confirms
- **THEN** the frontend makes a separate export request for 2023 and for 2024, and downloads a
  single ZIP containing the data from both

#### Scenario: Season with no data is omitted
- **WHEN** the user selects seasons 2023 and 2024 and the API reports no data for 2023
- **THEN** the downloaded ZIP contains only 2024 files and the export does not fail

#### Scenario: Loading state during export
- **WHEN** export requests are in flight
- **THEN** the dialog shows a loading indicator and the confirm button is disabled

### Requirement: Surface export errors inline
When any season's export request fails (other than the API reporting no data for that season), or
when every selected season has no data, the dialog SHALL abort the export, surface the error inline
(via the shared error alert), and remain open so the user can retry, rather than downloading a
file.

#### Scenario: Export failure shows inline error
- **WHEN** an export request returns an error
- **THEN** the dialog shows an inline error message, stays open, and no file is downloaded

#### Scenario: One season failing aborts the whole export
- **WHEN** the user selects seasons 2023 and 2024 and the request for 2023 succeeds but the request
  for 2024 fails with a server error
- **THEN** the dialog shows an inline error, stays open, and no file is downloaded

#### Scenario: All selected seasons have no data
- **WHEN** the API reports no data for every selected season
- **THEN** the dialog shows an inline error, stays open, and no file is downloaded

### Requirement: Export includes a data guide
The export ZIP's `README.md` SHALL describe the export so an AI assistant or person can interpret it
without other context. It SHALL state the league id, platform, exported seasons, and export time;
list every data file actually included; give a data dictionary (summary plus field descriptions) for
each view present in the export, including the keys used to join views (`team_id` / `roster_id` /
`owner_id`, `season`, `week`); note that views with no data are omitted rather than included empty;
include platform-specific caveats only for the export's platform; and suggest example questions to
ask an AI assistant. A view with no documentation entry SHALL still be listed, marked as
undocumented, rather than failing the export.

#### Scenario: README lists only included files
- **WHEN** the export bundle contains `standings` and `matchups` for `2024` only
- **THEN** the README lists `2024_standings.json` and `2024_matchups.json`, documents those two
  views, and does not document views absent from the bundle

#### Scenario: Platform caveats scoped to the export's platform
- **WHEN** an ESPN league's export includes `transactions`
- **THEN** the README notes that ESPN transactions cover only the current season with no draft-pick
  trades, and a Sleeper export's README does not include that ESPN note

#### Scenario: Undocumented view does not break the export
- **WHEN** the export bundle contains a view key that has no documentation entry
- **THEN** the README lists that view's files and marks the view as undocumented, and the ZIP is
  still produced

### Requirement: Export includes a machine-readable manifest
The export ZIP's `manifest.json` SHALL be a JSON object with `league_id`, `platform`, `exported_at`
(ISO 8601), `seasons` (the exported seasons, sorted ascending), and `files`: one entry per data file
with its `path`, `season`, `view`, and `row_count`.

#### Scenario: Manifest describes every data file
- **WHEN** a successful export includes `2023_standings.json` with 10 rows
- **THEN** `manifest.json`'s `files` contains an entry
  `{ "path": "2023_standings.json", "season": "2023", "view": "standings", "row_count": 10 }`

### Requirement: Export dialog suggests AI usage
The export dialog SHALL show a short hint that the downloaded ZIP can be uploaded to an AI
assistant (such as Claude or ChatGPT) to ask questions about the league, with a few example
prompts.

#### Scenario: AI hint shown
- **WHEN** the export dialog opens for a connected league
- **THEN** it shows a hint about uploading the export to an AI assistant, with example prompts
