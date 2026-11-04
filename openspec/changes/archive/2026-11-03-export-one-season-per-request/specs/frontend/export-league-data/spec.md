# Spec Delta

## MODIFIED Requirements

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
