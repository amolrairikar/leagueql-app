## ADDED Requirements

### Requirement: Skip ESPN leagues whose stored cookies were rejected

The Lambda SHALL NOT dispatch a refresh for a selected ESPN league whose owner's
`ESPN_CREDENTIALS` item carries `auth_failed_at`, so dead cookies are not sent to ESPN on every
run. Once the owner re-stores their cookies (which clears the flag), the league SHALL be selected
again.

#### Scenario: Owner's cookies flagged

- **WHEN** an opted-in ESPN league's owner has `auth_failed_at` on their `ESPN_CREDENTIALS` item
- **THEN** the run does not invoke the onboarder for that league and continues with the others

#### Scenario: Owner re-stored cookies

- **WHEN** an opted-in ESPN league's owner has an `ESPN_CREDENTIALS` item without `auth_failed_at`
- **THEN** the league is selected and refreshed as usual
