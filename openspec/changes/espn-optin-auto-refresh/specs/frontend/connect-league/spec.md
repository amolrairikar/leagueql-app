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

## MODIFIED Requirements

### Requirement: Private ESPN credentials handling

Private ESPN onboarding SHALL accept `s2`/`swid` via extension auto-fill or manual entry, transmit
them once over HTTPS, clear them from the browser on success, and never log them or keep them in
browser storage. The backend persists them (encrypted at rest) only when the user opts into
automatic refresh (backend/espn-credential-storage); without opt-in they are used only for the
request and not stored.

#### Scenario: Cookies via extension or manual

- **WHEN** a private ESPN league is onboarded
- **THEN** cookies can be auto-filled by the extension or entered manually, and are cleared
  (`clearEspnCookies`) on success

#### Scenario: Extension detection

- **WHEN** the extension is detected
- **THEN** an "Autofill cookies from ESPN" button is shown; when not detected, an inline Chrome Web
  Store install link is shown instead

#### Scenario: Credentials never persisted

- **WHEN** ESPN cookies are submitted
- **THEN** they appear in no logs and are not kept in browser storage; on the server they are stored
  (encrypted at rest) only when the user enabled automatic refresh, and are otherwise not persisted
