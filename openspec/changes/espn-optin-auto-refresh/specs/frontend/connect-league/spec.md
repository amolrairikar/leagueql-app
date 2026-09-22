## ADDED Requirements

### Requirement: Opt an ESPN league into automatic refresh

The ESPN connect/refresh form SHALL present an "enable automatic weekly refresh" checkbox with an
explanatory tooltip, defaulting to off for a new onboard and prefilled from the league's current
enrollment when refreshing an existing league. When checked, the form SHALL send the opt-in with the
`POST /leagues` submit so the owner's cookies are stored for reuse; when unchecked, it SHALL send the
opt-out. The tooltip SHALL explain that enabling stores the ESPN cookies encrypted to refresh the
league weekly during the season and that cookies can expire, occasionally requiring re-entry.

#### Scenario: Checkbox present with tooltip

- **WHEN** the ESPN connect/refresh form renders
- **THEN** an "enable automatic weekly refresh" checkbox is shown with a tooltip explaining that the
  ESPN cookies are stored encrypted, the league is refreshed weekly during the season, and cookies
  can expire and occasionally need re-entering

#### Scenario: Default off for a new onboard

- **WHEN** a user onboards a new ESPN league
- **THEN** the automatic-refresh checkbox defaults to unchecked (opt-in)

#### Scenario: Prefilled from current enrollment on refresh

- **WHEN** the form opens for an existing ESPN league the caller owns
- **THEN** the checkbox reflects that league's current `auto_refresh_enabled` state

#### Scenario: Choice sent with submit

- **WHEN** the user submits the ESPN form
- **THEN** the automatic-refresh opt-in choice is included in the `POST /leagues` request body
