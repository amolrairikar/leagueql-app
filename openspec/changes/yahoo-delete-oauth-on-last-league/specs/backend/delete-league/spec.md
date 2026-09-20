# Spec Delta

## ADDED Requirements

### Requirement: Remove orphaned Yahoo OAuth credentials on last Yahoo league delete
When a deleted league's effective platform is Yahoo, the API SHALL delete the owner's stored `YAHOO_OAUTH` token item once the owner no longer owns any other Yahoo league, and SHALL leave it in place while any other Yahoo league they own remains. Deleting an ESPN or Sleeper league SHALL never remove a `YAHOO_OAUTH` item. This cleanup is best-effort: a failure to remove the token item is logged/alerted but does not fail the league deletion.

#### Scenario: Owner's last Yahoo league deleted
- **WHEN** the owner deletes their only remaining Yahoo league
- **THEN** their `YAHOO_OAUTH` token item (`PK=USER#{clerk_user_id}, SK=YAHOO_OAUTH`) is removed along with the league's data

#### Scenario: Owner still has other Yahoo leagues
- **WHEN** the owner deletes one Yahoo league but still owns at least one other Yahoo league
- **THEN** the league's data is removed but the owner's `YAHOO_OAUTH` token item is left intact

#### Scenario: Non-Yahoo league deleted
- **WHEN** the owner deletes an ESPN or Sleeper league
- **THEN** no `YAHOO_OAUTH` item is read or removed

#### Scenario: Token cleanup failure does not fail the delete
- **WHEN** the league's items and S3 payloads are deleted but removing the `YAHOO_OAUTH` item raises a client error
- **THEN** the API still returns `200` for the league deletion and the token-cleanup failure is logged/alerted
