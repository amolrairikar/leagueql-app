## ADDED Requirements

### Requirement: Flag stored ESPN cookies that ESPN rejected

When a scheduled ESPN refresh that used a user's stored cookies is rejected by ESPN for auth, the
system SHALL record an `auth_failed_at` timestamp on that user's `ESPN_CREDENTIALS` item. The mark
SHALL apply only if the item still holds the version the refresh used (same `updated_at`), and
re-storing the user's cookies SHALL clear the flag.

#### Scenario: Rejected stored cookies flagged

- **WHEN** a scheduled ESPN refresh using the owner's stored cookies records an `ESPN_AUTH` failure
- **THEN** the owner's `ESPN_CREDENTIALS` item gains an `auth_failed_at` timestamp

#### Scenario: Cookies replaced mid-run are not flagged

- **WHEN** the owner re-stores their cookies after a scheduled refresh read them but before it
  records the rejection
- **THEN** the newly stored item is left without `auth_failed_at`

#### Scenario: Re-storing cookies clears the flag

- **WHEN** a user's cookies are stored again (a successful opted-in refresh, or an opted-in blocked
  refresh whose cookies authenticate)
- **THEN** the stored `ESPN_CREDENTIALS` item has no `auth_failed_at`
