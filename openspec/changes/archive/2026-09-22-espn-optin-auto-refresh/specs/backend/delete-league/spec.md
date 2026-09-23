## ADDED Requirements

### Requirement: Remove orphaned ESPN credentials on last opted-in ESPN league delete

When a deleted league's effective platform is ESPN, the API SHALL delete the owner's stored
`ESPN_CREDENTIALS` item once the owner no longer has any other ESPN league opted into automatic
refresh, and SHALL leave it in place while any other opted-in ESPN league they own remains.
Deleting a Yahoo or Sleeper league SHALL never remove an `ESPN_CREDENTIALS` item. The entire
cleanup — the check for other opted-in ESPN leagues and the credential deletion — SHALL be
best-effort: because the league's data is already deleted before it runs, any failure within it
(including the ownership-check query) SHALL be logged/alerted and SHALL NOT fail the league
deletion.

#### Scenario: Owner's last opted-in ESPN league deleted

- **WHEN** the owner deletes their only remaining ESPN league that was opted into automatic refresh
- **THEN** their `ESPN_CREDENTIALS` item (`PK=USER#{clerk_user_id}, SK=ESPN_CREDENTIALS`) is removed
  along with the league's data

#### Scenario: Owner still has other opted-in ESPN leagues

- **WHEN** the owner deletes one ESPN league but still has at least one other ESPN league opted into
  automatic refresh
- **THEN** the league's data is removed but the owner's `ESPN_CREDENTIALS` item is left intact

#### Scenario: Non-ESPN league deleted

- **WHEN** the owner deletes a Yahoo or Sleeper league
- **THEN** no `ESPN_CREDENTIALS` item is read or removed

#### Scenario: Credential cleanup failure does not fail the delete

- **WHEN** the league's items and S3 payloads are deleted but removing the `ESPN_CREDENTIALS` item,
  or the ownership-check query, raises an error
- **THEN** the API still returns `200` for the league deletion, no credentials removal is required to
  succeed, and the failure is logged/alerted
