# Design

## Which records count as a completed trade

| ESPN `type` | `status` | Role |
|---|---|---|
| `TRADE_PROPOSAL` | any | Never a completed trade; not stored |
| `TRADE_ACCEPT` | `PENDING` or missing | Not completed on its own; ignored |
| `TRADE_ACCEPT` | `EXECUTED` | Completed (a league with no review period), or the player-card record carrying the traded players |
| `TRADE_UPHOLD` | `EXECUTED` | Completed; the trade cleared review |

The onboarder keeps EXECUTED `FREEAGENT`/`WAIVER`/`TRADE_UPHOLD`/`TRADE_ACCEPT` records, with
their `ADD`/`DROP`/`TRADE` items, `relatedTransactionId`, and `acceptedDate`.

## Hidden trades

`mTransactions2` returns a trade's players only when the requesting team is a party. For any other
trade the executed record has no `TRADE` items (the 2026 uphold had no `items` key at all). A
**hidden trade** is an executed `TRADE_UPHOLD`/`TRADE_ACCEPT` with no `TRADE` items.

## Recovering hidden trades from player cards

After the regular fetch, `ESPNClient.fetch_all` runs a second step for the latest season:

1. Collect the hidden trades from the filtered `transactions_week{N}` results. Each trade's key is
   its `relatedTransactionId`, or its `id` when there is none.
2. Candidate players are every `playerId` in the `rosterForCurrentScoringPeriod` /
   `rosterForMatchupPeriod` entries of the season's `matchups_week{N}` and `matchups_week{N+1}`
   results, for each hidden trade's week `N`. Weeks `N` and `N+1` together cover the traded players
   whether the box score shows the roster before or after the trade.
3. Request `view=kona_playercard` on the season's league URL in batches of 40 player IDs, with an
   `X-Fantasy-Filter` of `{"players": {"filterIds": {"value": [...]}}}`.
4. Each card's transactions are read from `transactions` on the player wrap (or on its nested
   `player`). Keep the EXECUTED `TRADE_ACCEPT` records that have `TRADE` items and whose key
   (`relatedTransactionId`, else `id`) matches a hidden trade, choosing the record with the most
   `TRADE` items per key.
5. The chosen records are trimmed like any other transaction and returned as one extra result,
   `{"season", "data_type": "transactions_trade_cards", "data": {"transactions": [...]}}`. The
   processor already collects every `transactions*` data type, so it needs no new input path.

Card requests are only made in weeks that have a hidden trade (about four requests for a 10-team
league). A failed card request is logged as a warning and the step returns what it recovered; the
trade it would have filled is then skipped by the processor, so a card problem never fails an
onboarding or refresh.

## Grouping one trade's records

The processor builds one row per completed trade by grouping trade records under a key:

- `(season, relatedTransactionId)` when the record has one, else `(season, id)`. A card record and
  an uphold for the same trade share the `relatedTransactionId`.
- For records with no `relatedTransactionId` (the 2018 sample) and that do have `TRADE` items, the
  2018 content key `(season, processDate, frozenset of (playerId, fromTeamId, toTeamId))` is used,
  so a 2018 accept + uphold pair still collapses to one row.

Within a group:

- **Completed:** at least one record is EXECUTED (every stored trade record is).
- **Traded players:** the `TRADE` items of the record with the most of them, plus any `DROP` items
  on the group's records (players a team released to make room), deduplicated.
- **Row record:** the `TRADE_UPHOLD` when present, otherwise the executed `TRADE_ACCEPT`. Its `id`
  is the `transaction_id`, and `created` is its `processDate`, else `acceptedDate`, else
  `proposedDate` (the 2026 uphold has only `proposedDate`, written when it was upheld).
- **No players:** a group with no `TRADE` items writes no row and logs a warning.

## Trade row shape

- Each `TRADE` item becomes a drop resolved against `fromTeamId` and an add resolved against
  `toTeamId`, matching `compile_yahoo_transactions`. A `DROP` item becomes a drop for its team.
- `roster_ids` are the item teams in first-seen order (deduplicated); `txn.teamId` is not used for
  trades, since on an uphold it identifies the upholding team.
- `week` is `scoringPeriodId`; `draft_picks` stays empty; `waiver_bid` is `bidAmount`.

## Risk

The card response shape (where `transactions` sits on a card, and that a card's `TRADE_ACCEPT`
carries the full `TRADE` items) comes from reading the `espn-api` library
(`espn_api/utils/trade_fill.py`), not from a live response. The parsing accepts both locations the
library checks. Before release, confirm it against a live league with a hidden trade (task 1.9).
