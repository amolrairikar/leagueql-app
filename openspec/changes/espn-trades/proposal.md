# Proposal

## Why

ESPN leagues show no trades on `/transactions`. The ESPN onboarder keeps only EXECUTED `FREEAGENT`
and `WAIVER` records from `mTransactions2`, and the page hides the Trades filter and summary column
for ESPN. Sleeper and Yahoo both store `trade` rows, so ESPN is the only platform without them.

The ESPN API returns a completed trade as several records that list the same items under different
`id`s: a `TRADE_PROPOSAL` (stays `PENDING`, or gets `executionType: CANCEL` when withdrawn), a
`TRADE_ACCEPT` (`PENDING` during the league's review period), and a `TRADE_UPHOLD` that is
`EXECUTED` when the review period ends. The upheld record's `teamId` is not one of the trading
teams. A league without a review period is expected to record the accept itself as `EXECUTED`.

## What Changes

- The ESPN onboarder also keeps EXECUTED `TRADE_UPHOLD` and `TRADE_ACCEPT` records and their
  `TRADE` items.
- The processor stores them as `type: "trade"` rows in the existing transactions view: each
  traded player is a drop from its source team and an add to its destination team (the Yahoo and
  Sleeper trade shape). `roster_ids`/`teams` list both trading teams, taken from the items, and
  `created` is the execution time (`processDate`).
- When both an EXECUTED accept and an EXECUTED uphold exist for the same trade, only one row is
  stored (the uphold).
- `/transactions` offers the Trades filter (defaulting to Trades) and the Trades summary column for
  ESPN, the same as for Sleeper and Yahoo.
- No schema change. Existing ESPN leagues pick up trades on their next refresh.
