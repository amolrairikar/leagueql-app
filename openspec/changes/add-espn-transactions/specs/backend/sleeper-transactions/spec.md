## MODIFIED Requirements

### Requirement: No item for empty transactions
A Sleeper league/season with no completed transactions SHALL write no `TRANSACTIONS#{season}` item (of any chunk). ESPN leagues also produce `TRANSACTIONS` items now (see `backend/espn-transactions`), so this is no longer Sleeper-exclusive.

#### Scenario: No transactions
- **WHEN** a Sleeper season has no completed transactions
- **THEN** no `TRANSACTIONS#{season}` item (of any chunk) is written and a query for it returns `404`

#### Scenario: ESPN league
- **WHEN** an ESPN league's current season has completed (EXECUTED) waiver/free-agent transactions
- **THEN** it produces `TRANSACTIONS#{season}` items (per `backend/espn-transactions`) and is no longer suppressed
