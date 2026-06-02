# FE-012: Draft Recap (Draft Board)

## Description
The `/draft_recap` page renders a draft board for a selected season. For snake drafts it
shows the classic round-by-round grid with the overall pick number per cell. For auction
drafts it shows a spend board with the winning bid per pick. Each pick cell is colored by
position and shows the player's season points.

## Scope
- Route: `/draft_recap` (protected, app layout).
- Component: `src/features/draft_recap/draft-recap.tsx`; API in `api-calls.ts`.
- Reads `DRAFT#{season}` via [BE-005](../backend/BE-005-query-precomputed-views-api.md).

## Edge Cases
- **Snake vs. auction:** board layout differs — snake grid shows overall pick number;
  auction spend board shows `bid_amount`. Detect draft type from pick data.
- **Keeper picks:** indicate keepers; ESPN may also have `reserved_for_keeper` slots.
- **Missing player name/points:** cells tolerate null `player_name`/`total_points`.
- **Pinned/sticky context:** the board supports pinning a row/column for reading large grids
  (see `draft-recap-pinned.png`).
- **Varying roster/round counts:** grid adapts to the league's number of teams and rounds.
- **Sleeper picks:** `pick_id` null for Sleeper; do not rely on it.

## Acceptance Criteria
- [ ] `/draft_recap` renders a snake draft grid with overall pick numbers for snake leagues.
- [ ] Auction drafts render a spend board showing winning bids.
- [ ] Each cell is colored by position and shows the player's season points when available.
- [ ] Keeper picks are visually indicated.
- [ ] The board adapts to the league's team and round counts and handles null player data.

## Sources
`src/features/draft_recap/`, `draft-recap-initial.png`, `draft-recap-pinned.png`.
