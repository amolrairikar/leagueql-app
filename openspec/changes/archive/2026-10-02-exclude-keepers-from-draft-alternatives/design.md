# Design

## Context

`getAlts(pick, allPicks, isAuction)` in `draft-grades.tsx` builds up to two alternatives for a
bust. For snake drafts these are same-position players from other teams who were picked later
(within `ALT_PICK_ROUND_WINDOW` rounds) and scored more. For auctions they are same-position
players who cost the same or less and scored more. `bustsWithAlts` drops busts that end up with
zero alternatives, which hides both the desktop expansion row and the mobile card.

`DraftPickItem.keeper` comes from ESPN (`keeper`) and Sleeper (`is_keeper`). Yahoo sends `NULL`.

## Decisions

- **Filter on the client in `getAlts`.** The client already has the `keeper` flag, and the
  alternatives are computed entirely on the client. No backend change is needed.
- **A keeper bust returns `[]` early.** This reuses the existing "no alternatives means no
  panel" path. The bust classification (`isBustPick`) stays the same, because a keeper can still
  underperform.
- **Treat a falsy `keeper` (including `null`) as not a keeper.** Yahoo has no keeper data, and
  Yahoo leagues should keep working as they do today.
