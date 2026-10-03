## ADDED Requirements

### Requirement: Report ESPN re-authentication required

The league metadata response SHALL include `espn_reauth_required` (boolean) and
`espn_credentials_failed_at` (ISO 8601, nullable). `espn_reauth_required` SHALL be true only when
the caller is the league owner, the league is an ESPN league with `auto_refresh_enabled`, and the
owner's `ESPN_CREDENTIALS` item is missing or carries `auth_failed_at`.
`espn_credentials_failed_at` SHALL carry that `auth_failed_at` when present. Both SHALL be
false/null for every other caller or league.

#### Scenario: Owner with rejected cookies

- **WHEN** the owner reads an auto-refresh-enabled ESPN league and their stored credentials carry
  `auth_failed_at`
- **THEN** the response has `espn_reauth_required` true and `espn_credentials_failed_at` set to that
  timestamp

#### Scenario: Owner with missing cookies

- **WHEN** the owner reads an auto-refresh-enabled ESPN league and has no stored credentials
- **THEN** the response has `espn_reauth_required` true and `espn_credentials_failed_at` null

#### Scenario: Healthy cookies or not enrolled

- **WHEN** the owner's stored credentials carry no `auth_failed_at`, or the league is not enrolled
  in auto-refresh, or the league is not an ESPN league
- **THEN** the response has `espn_reauth_required` false

#### Scenario: Non-owner

- **WHEN** a member who is not the owner reads the league
- **THEN** the response has `espn_reauth_required` false and `espn_credentials_failed_at` null
