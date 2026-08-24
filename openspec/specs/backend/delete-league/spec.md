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
