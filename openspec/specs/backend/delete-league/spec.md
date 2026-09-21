# delete-league Specification

## Purpose
Delete an onboarded league and all of its associated data. `DELETE /leagues/{leagueId}` resolves the canonical league ID, removes every DynamoDB item for the league, deletes the raw API payloads from S3, and decrements the global `LEAGUE_COUNT`.

## Requirements

### Requirement: Delete an onboarded league
The API SHALL delete an onboarded league and return `200` on success.

#### Scenario: Onboarded league is deleted
- **WHEN** `DELETE /leagues/{leagueId}` is called for an onboarded league by its owner
- **THEN** the API returns `200` with "Successfully deleted league"

#### Scenario: League is not onboarded
- **WHEN** `DELETE /leagues/{leagueId}` is called for a league whose ID is absent from `LEAGUE_LOOKUP`
- **THEN** the API returns `404`

### Requirement: Remove all DynamoDB items for the league
The API SHALL remove every DynamoDB item for the canonical league, including its `METADATA`, all `LEAGUE_LOOKUP` entries, and all precomputed view items.

#### Scenario: All items removed
- **WHEN** an onboarded league is deleted
- **THEN** no `METADATA`, `LEAGUE_LOOKUP`, or precomputed view items remain for the canonical league

#### Scenario: Migrated league with lookups across platforms
- **WHEN** the canonical league has multiple `LEAGUE_LOOKUP` entries across platforms and one is deleted
- **THEN** all lookup entries for that canonical league are removed, not only the one queried

### Requirement: Delete raw S3 payloads
The API SHALL delete all raw API payloads under the league's S3 prefix `raw-api-data/{canonical_league_id}/`.

#### Scenario: Raw payloads deleted
- **WHEN** an onboarded league is deleted
- **THEN** all objects under `raw-api-data/{canonical_league_id}/` are removed

#### Scenario: No S3 objects present
- **WHEN** the league has no objects under its S3 prefix
- **THEN** deletion still succeeds (S3 deletion is best-effort / a no-op when empty)

#### Scenario: More than 1000 S3 objects
- **WHEN** the league's S3 prefix holds more than 1000 objects
- **THEN** the deletion batches the keys so all objects are removed (S3 `delete_objects` accepts at most 1000 keys per request)

### Requirement: Decrement the global league count
The API SHALL decrement the global `LEAGUE_COUNT` by 1 when a league is deleted, without leaving the count inconsistent on repeated deletes.

#### Scenario: Count decremented once
- **WHEN** an onboarded league is deleted
- **THEN** `LEAGUE_COUNT` is decremented by 1

#### Scenario: Deleting an already-deleted league
- **WHEN** a delete is issued for a league that has already been deleted
- **THEN** `LEAGUE_COUNT` is not driven inconsistent

### Requirement: Report backend failures
The API SHALL return `500` "Failed to delete league" when a DynamoDB or S3 client error occurs during deletion.

#### Scenario: Backend client error
- **WHEN** a DynamoDB or S3 error occurs while deleting the league's data
- **THEN** the API returns `500` "Failed to delete league"

### Requirement: Owner-gated deletion
The API SHALL restrict deletion to the league owner, rejecting a non-owner before any data is touched.

#### Scenario: Non-owner attempts deletion
- **WHEN** a user who is not the league owner calls `DELETE /leagues/{leagueId}`
- **THEN** the API returns `403` and no DynamoDB or S3 data is modified

### Requirement: Remove orphaned Yahoo OAuth credentials on last Yahoo league delete
When a deleted league's effective platform is Yahoo, the API SHALL delete the owner's stored `YAHOO_OAUTH` token item once the owner no longer owns any other Yahoo league, and SHALL leave it in place while any other Yahoo league they own remains. Deleting an ESPN or Sleeper league SHALL never remove a `YAHOO_OAUTH` item. The entire cleanup — the check for other Yahoo leagues and the token deletion — SHALL be best-effort: because the league's data is already deleted before it runs, any failure within it (including the ownership-check query) SHALL be logged/alerted and SHALL NOT fail the league deletion. The API's execution role SHALL be granted the DynamoDB permission needed for the ownership-check query so the cleanup succeeds in normal operation.

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

#### Scenario: Ownership-check failure does not fail the delete
- **WHEN** the league's items and S3 payloads are deleted but the "other Yahoo leagues" ownership-check query raises an error (e.g. a missing GSI permission)
- **THEN** the API still returns `200` for the league deletion, no token is removed, and the failure is logged/alerted
