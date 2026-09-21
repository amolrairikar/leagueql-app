# Spec Delta

## ADDED Requirements

### Requirement: Delete stored tokens when no longer needed
The token engine SHALL support deleting a user's stored `YAHOO_OAUTH` token item, and this deletion SHALL be idempotent (deleting when no item exists is a no-op). The stored tokens SHALL be removed once the user no longer owns any Yahoo league, so no encrypted credentials are retained beyond their use.

#### Scenario: Delete token item
- **WHEN** `delete_tokens` is called for a user
- **THEN** the `YAHOO_OAUTH` item at `PK=USER#{clerk_user_id}, SK=YAHOO_OAUTH` is removed

#### Scenario: Delete is idempotent
- **WHEN** `delete_tokens` is called for a user with no stored token item
- **THEN** the call succeeds without error and no item is affected
