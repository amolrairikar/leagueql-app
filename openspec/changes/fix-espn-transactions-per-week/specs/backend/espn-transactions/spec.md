## MODIFIED Requirements

### Requirement: Fetch ESPN transactions for the current season only
Onboarding or refreshing an ESPN league SHALL fetch transactions from the `mTransactions2` view for the latest (current) season only, issuing one request per scoring period (week) of that season — each request carrying that week's `scoringPeriodId` — because a `mTransactions2` request without a `scoringPeriodId` returns only the current scoring period's transactions. The per-week payloads SHALL be combined into the season's transactions view. The system SHALL NOT request transactions for any earlier season.

#### Scenario: Only the latest season is requested
- **WHEN** an ESPN league with multiple onboarded seasons is fetched
- **THEN** transactions requests are issued only for the latest season, one per scoring period (week) of that season, and no transactions request is issued for any earlier season

#### Scenario: Transactions across multiple weeks are all captured
- **WHEN** the latest season has completed transactions in more than one scoring period (e.g. weeks 1, 2, and 3)
- **THEN** the season's transactions view contains the stored transactions from every one of those weeks, not only the most recent scoring period

#### Scenario: No transactions request when the latest season is undrafted
- **WHEN** an ESPN league's latest season has not yet drafted (it produces no data and is excluded)
- **THEN** no transactions request is issued for any week

#### Scenario: Weeks with no transactions are tolerated
- **WHEN** a scoring period of the latest season (for example an unplayed future week) returns no transactions
- **THEN** that week contributes no rows and the run succeeds, combining the remaining weeks' transactions into the season's view
