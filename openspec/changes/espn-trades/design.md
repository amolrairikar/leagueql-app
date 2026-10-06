# Design

## Which records count as a completed trade

| ESPN `type` | `status` | Stored? |
|---|---|---|
| `TRADE_PROPOSAL` | any | No; a proposal is never a completed trade |
| `TRADE_ACCEPT` | `PENDING` | No; still in the review period |
| `TRADE_ACCEPT` | `EXECUTED` | Yes; a league with no review period |
| `TRADE_UPHOLD` | `EXECUTED` | Yes; the trade cleared review |

The existing `status == "EXECUTED"` filter already drops pending and cancelled records, so the
onboarder only has to allow the two extra types and the `TRADE` item type.

## Trade row shape

- Each `TRADE` item becomes a drop resolved against `fromTeamId` and an add resolved against
  `toTeamId`, matching `compile_yahoo_transactions`.
- `roster_ids` are the item teams in first-seen order (deduplicated). `txn.teamId` is not used for
  trades: on an uphold it identifies the team that upheld the trade, not a party to it.
- `created` uses `processDate`, the same as waivers. `week` is `scoringPeriodId`. `draft_picks`
  stays empty (ESPN draft-pick trades are not in the payload).

## One row per trade

The accept and the uphold for a trade have different `id`s. They share `processDate` and the
exact set of `(playerId, fromTeamId, toTeamId)` items, so that tuple (with the season) is the trade
key. Records are processed with upholds before accepts, so the uphold's `id` is the one kept. The
existing `(season, id)` dedupe still handles a record repeated by overlapping per-week fetches.
