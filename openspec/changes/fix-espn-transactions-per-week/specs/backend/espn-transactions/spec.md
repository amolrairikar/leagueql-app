## MODIFIED Requirements

### Requirement: Fetch ESPN transactions for the current season only
Onboarding or refreshing an ESPN league SHALL fetch transactions from the `mTransactions2` view for the latest (current) season only, issuing one request per scoring period (week) up to and including the season's current scoring period — each request carrying that week's `scoringPeriodId` — because a `mTransactions2` request without a `scoringPeriodId` returns only the current scoring period's transactions, and a request for any scoring period at or beyond the current one returns (and would duplicate) the current period's transactions. When the current scoring period is unknown, the system MAY request the full week range and SHALL rely on deduplication to keep each transaction once. The per-week payloads SHALL be combined into the season's transactions view, with each transaction stored exactly once regardless of how many per-week requests returned it. The system SHALL NOT request transactions for any earlier season.

#### Scenario: Only the latest season is requested
- **WHEN** an ESPN league with multiple onboarded seasons is fetched and the latest season's current scoring period is known
- **THEN** transactions requests are issued only for the latest season, one per scoring period from week 1 through the current scoring period, and no transactions request is issued for any earlier season or for any week beyond the current scoring period

#### Scenario: Transactions across multiple weeks are all captured
- **WHEN** the latest season has completed transactions in more than one scoring period (e.g. weeks 1, 2, and 3)
- **THEN** the season's transactions view contains the stored transactions from every one of those weeks, not only the most recent scoring period

#### Scenario: A transaction returned by more than one week is stored once
- **WHEN** the same transaction is returned by more than one per-week request (for example the current period's transactions echoed by a request at or beyond the current scoring period)
- **THEN** that transaction appears exactly once in the season's transactions view

#### Scenario: No transactions request when the latest season is undrafted
- **WHEN** an ESPN league's latest season has not yet drafted (it produces no data and is excluded)
- **THEN** no transactions request is issued for any week

#### Scenario: Weeks with no transactions are tolerated
- **WHEN** a scoring period of the latest season returns no transactions
- **THEN** that week contributes no rows and the run succeeds, combining the remaining weeks' transactions into the season's view
