## ADDED Requirements

### Requirement: Derive the league count
The league count SHALL be derived as the number of league `METADATA` items, computed by querying
the `SK = "METADATA"` index (GSI3) with `Select=COUNT` and summing the count across all paginated
result pages, and published to the counts KV store on the existing hourly cadence.

#### Scenario: Count reflects existing leagues
- **WHEN** the hourly counts sync runs and there are N league `METADATA` items
- **THEN** the published count equals N, summed across every paginated page of the `SK="METADATA"` query

#### Scenario: Self-healing after drift
- **WHEN** a league is added or removed by any path (onboard, delete, orphan cleanup, or manual data change)
- **THEN** the next hourly sync recomputes the count from the current `METADATA` items, with no separately maintained counter to keep in sync

#### Scenario: No maintained counter
- **WHEN** a league is onboarded or deleted
- **THEN** no increment/decrement is written to an `APP#STATS`/`LEAGUE_COUNT` item (that item is retired)

## MODIFIED Requirements

### Requirement: Refresh and migrate do not change the count
Refresh and migration SHALL leave the count unchanged (same canonical league, one `METADATA` item).

#### Scenario: Refresh/migrate
- **WHEN** a league is refreshed or migrated
- **THEN** the derived count is unchanged, because the canonical league still has exactly one `METADATA` item

## REMOVED Requirements

### Requirement: Maintain the league count
**Reason**: Replaced by a derived count computed from the `METADATA` items in GSI3, which is
self-healing and cannot drift. The maintained atomic counter and its `APP#STATS`/`LEAGUE_COUNT`
item are retired.
**Migration**: None required. The counts sync now derives the value from `METADATA` items instead
of reading the counter; the retired item can be deleted or left to expire unused.
