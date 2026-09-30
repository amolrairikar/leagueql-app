## ADDED Requirements

### Requirement: Fetch each Yahoo season's week calendar
Onboarding or refreshing a Yahoo league SHALL fetch the week calendar (each week's start and end
date) for every onboarded season, so the processor can place undated-by-week data such as
transactions into weeks.

#### Scenario: Week calendar fetched per season
- **WHEN** a Yahoo league with one or more onboarded seasons is onboarded or refreshed
- **THEN** a week calendar listing each week's number, start date, and end date is stored with
  every season's raw data
