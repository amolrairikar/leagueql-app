# Spec Delta

## MODIFIED Requirements

### Requirement: Download selected seasons as a ZIP of JSON files
On confirm, the frontend SHALL request the export for the selected seasons and download the result
to the browser as a single ZIP file containing one JSON file per view per season (named
`<season>_<view>.json`), plus a `README.md` data guide and a `manifest.json` at the ZIP root. A
loading indicator SHALL be shown while the export is in progress.

#### Scenario: Successful export downloads a ZIP
- **WHEN** the user selects one or more seasons and confirms, and the request succeeds
- **THEN** a ZIP file is downloaded containing one JSON file per view per selected season, a
  `README.md`, and a `manifest.json`

#### Scenario: Loading state during export
- **WHEN** an export request is in flight
- **THEN** the dialog shows a loading indicator and the confirm button is disabled

## ADDED Requirements

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
