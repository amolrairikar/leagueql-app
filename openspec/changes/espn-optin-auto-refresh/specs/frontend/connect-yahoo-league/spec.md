## ADDED Requirements

### Requirement: Opt a Yahoo league into automatic refresh

The Yahoo connect flow SHALL present an "enable automatic weekly refresh" checkbox with an
explanatory tooltip, defaulting to off, and SHALL record the owner's choice so the scheduled refresh
honors it. Because Yahoo authorization is already stored, enabling only sets the league's opt-in; no
additional credentials are collected. The tooltip SHALL explain that enabling refreshes the league
weekly during the season using the existing Yahoo authorization.

#### Scenario: Checkbox present with tooltip

- **WHEN** the Yahoo connect flow renders for a league the caller will own
- **THEN** an "enable automatic weekly refresh" checkbox is shown with a tooltip explaining the league
  is refreshed weekly during the season using the stored Yahoo authorization

#### Scenario: Default off (opt-in)

- **WHEN** the Yahoo connect flow renders
- **THEN** the automatic-refresh checkbox defaults to unchecked

#### Scenario: Choice recorded

- **WHEN** the user completes the Yahoo connect flow with the checkbox checked
- **THEN** the league is recorded as opted into automatic refresh
