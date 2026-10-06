# Proposal

## Why

ESPN leagues show no trades on `/transactions`. The ESPN onboarder keeps only EXECUTED `FREEAGENT`
and `WAIVER` records from `mTransactions2`, and the page hides the Trades filter and summary column
for ESPN. Sleeper and Yahoo both store `trade` rows, so ESPN is the only platform without them.

The ESPN API records one trade as several records under different `id`s: a `TRADE_PROPOSAL`, a
`TRADE_ACCEPT`, and (in leagues with a review period) a `TRADE_UPHOLD` that becomes `EXECUTED`
when the trade clears review. The records are linked by `relatedTransactionId` (current seasons;
the 2018 sample had no link). The uphold's `teamId` is not one of the trading teams.

**`mTransactions2` hides the traded players of trades that don't involve the requesting team.** In
a 2026 league, the executed `TRADE_UPHOLD` came back with no `items` and no `processDate`, the
`TRADE_ACCEPT` came back with no `status` and only an accept-time `DROP`, and the `TRADE_PROPOSAL`
holding the players was not returned at all. Storing the uphold alone produced a trade row with no
players. The players are available from the player cards (`kona_playercard`) of the traded
players: each card lists that player's transactions, including the executed `TRADE_ACCEPT` with its
`TRADE` items. This is the approach the `espn-api` library uses (`fill_trade_items`).

## What Changes

- The ESPN onboarder also keeps EXECUTED `TRADE_UPHOLD` and `TRADE_ACCEPT` records (with
  `relatedTransactionId`, `acceptedDate`, and their `TRADE` items).
- When a week contains an executed trade with no traded players, the onboarder fetches the player
  cards of every player rostered in that week and the next, picks the executed `TRADE_ACCEPT` with
  the most traded players for each hidden trade, and stores those records with the season's
  transactions. A failed card fetch is logged and does not fail the run.
- The processor groups a trade's records by `relatedTransactionId` (falling back to the record's
  own `id`, and to the trade's content for records with no link), takes the traded players from
  whichever record has them, and stores one `type: "trade"` row per completed trade: each traded
  player is a drop from its source team and an add to its destination team (the Yahoo and Sleeper
  trade shape), and `roster_ids`/`teams` list both trading teams. A trade whose players cannot be
  recovered is not stored.
- `/transactions` offers the Trades filter (defaulting to Trades) and the Trades summary column for
  ESPN, the same as for Sleeper and Yahoo.
- No schema change. Existing ESPN leagues pick up trades on their next refresh.
