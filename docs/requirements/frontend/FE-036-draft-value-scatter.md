# FE-036: Draft Value Scatter (Draft Recap)

## Description
A free section on the **Draft Recap** page (`/draft_recap`), shown below the draft board under
the header **"Draft value"**: a **scatterplot** of every drafted player, with **draft position**
(the overall pick number) on the x-axis and **season points scored** on the y-axis. Each dot is one
pick, colored by position, so the shape of draft value reads at a glance — where the steals were
(late picks, high points) and where the busts were (early picks, low points). A single **position
dropdown** filters the dots to one position (or all), and the page-level **season selector** at the
top of the page drives which draft the scatter reads.

Everything is computed **entirely client-side** from the season's `DRAFT` view (the same
`getDraftData` the draft board already fetches), so there is no backend, no new DynamoDB view, and
no API change. It mirrors the Analytics charts
([FE-033](FE-033-analytics-page.md)): a pure transform of an existing precomputed view.

## Point construction
Each drafted pick becomes one dot:
- **x** = `overall_pick_number` (draft position; global chronological pick order).
- **y** = `total_points` (the player's season points).
- Tooltip fields = `player_name` (player), `owner_username` (the manager who drafted them),
  `total_points` (points scored), and `overall_pick_number` (draft position).
- Dots are colored by `position` from the shared position palette (`positionColorMeta`), so a
  position reads as its usual color across the app.

A pick is **plotted only when both axes are finite** — `total_points` and `overall_pick_number` must
be finite numbers. Picks with a null/absent `total_points` (e.g. Sleeper D/ST and kickers, or
players who never recorded stats — all null together from the same LEFT JOIN) are **omitted** from
the scatter rather than drawn at zero, so they don't create a false floor of busts.

## Position filter
- A single dropdown offers **All positions** plus every distinct `position` present in the season's
  draft data, ordered by `FANTASY_POSITION_ORDER` (QB → RB → WR → TE → D/ST → K → IDP …).
- Selecting a position filters the plotted dots to that position; **All positions** shows every dot.
- The filter is **local** to the scatter section and resets to **All positions** when the section
  mounts; it does not affect the draft board above.

## Scope
- Free section on the existing `/draft_recap` page ([FE-012](FE-012-draft-recap.md)), driven by
  the same page-level season selector (and, in demo mode, the snake/auction toggle).
- Component: `DraftValueScatter` wrapper + section in `src/features/draft_recap/draft-recap.tsx`;
  recharts scatter chart in `src/features/draft_recap/draft-scatter-chart.tsx`; pure transform in
  `src/features/draft_recap/compute-draft-scatter.ts`; data fetch reuses `getDraftData`
  (`DRAFT#{season}`, [BE-005](../backend/BE-005-query-precomputed-views-api.md)).
- The chart is a **recharts `ScatterChart`** with a numeric x-axis (draft position) and numeric
  y-axis (points), colored per position from the shared palette
  (`positionColorMeta`, `src/lib/color-constants.ts`). Hovering a dot reveals a tooltip with the
  player name, drafting manager, points scored, and draft position. A legend below names each
  position present.
- **Free:** the section always renders for everyone (below the draft board, whenever the season has
  draft data); there is no subscription gating.

## Edge Cases
- **Missing scoring (null `total_points`):** the pick is omitted from the scatter (not drawn at
  zero), so unscored Sleeper D/ST and kickers don't form a false floor.
- **Missing player name:** a null `player_name` falls back to a placeholder label in the tooltip;
  the dot still plots.
- **Auction drafts:** `overall_pick_number` remains the nomination order, so dots still plot along
  the x-axis; the demo snake/auction toggle selects the matching dataset.
- **Unusual / IDP positions:** any position without a dedicated color falls back to the kicker
  palette (matching the draft boards) and still appears in the dropdown.
- **Empty position filter:** selecting a position with no scored picks renders an empty plot area
  rather than crashing.
- **No `DRAFT` data (404) or load failure:** surface an inline message; never throw.
- **No scored picks at all:** show an empty-state message instead of an empty chart.

## Acceptance Criteria
- [ ] The Draft Recap page renders a **Draft value** scatterplot below the draft board, one dot per
      scored pick for the selected season, with draft position on the x-axis and season points on
      the y-axis, colored by position with a legend.
- [ ] Each dot's tooltip shows the player name, the manager who drafted them, the points scored, and
      the draft position; the point construction is unit-tested.
- [ ] A pick with a null `total_points` is omitted from the scatter (never drawn at zero); the
      transform is unit-tested.
- [ ] A single position dropdown offers **All positions** plus each present position and filters the
      plotted dots; selecting a position with no scored picks does not crash.
- [ ] Switching the page season selector recomputes the scatter.
- [ ] The section renders for everyone, with no subscription gating.
- [ ] A `DRAFT` load failure renders an inline message, and a season with no scored picks renders an
      empty-state message — neither crashes.

## Sources
`src/features/draft_recap/` (`draft-recap.tsx`, `draft-scatter-chart.tsx`,
`compute-draft-scatter.ts`), `src/features/draft_grades/api-calls.ts` (`getDraftData`,
`DraftPickItem`), `src/lib/position-constants.ts` (`FANTASY_POSITION_ORDER`),
`src/lib/color-constants.ts` (`positionColorMeta`).
