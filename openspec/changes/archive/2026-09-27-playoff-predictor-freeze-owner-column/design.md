## Decisions

- **Same pattern as the other standings tables** (`season-standings`, `home-page`,
  `transactions`): `sticky left-0 z-10` on the first `th`/`td`, with an opaque background
  (`bg-muted` header, `bg-card` body) so scrolled cells don't show through.
- **Playoff-row tint.** Playoff rows tint the whole `<tr>` with translucent `bg-primary/10`. A
  sticky cell can't rely on that tint because the cells scrolling underneath would show through.
  So the frozen cell paints the same tint as a gradient layer (`bg-linear-to-r from-primary/10
  to-primary/10`) over opaque `bg-card`, and it matches the rest of the row.
- **Playoff line label.** The cutoff row is a single full-width `colSpan` cell, so its label is
  made `sticky left-3.5` within that cell to stay aligned with the frozen column.
- **Mobile width cap.** Below `sm`, the Seed · Owner `th`/`td` get a fixed `w-67` (268px),
  matching Season Standings' owner column on a phone (38% of its 720px minimum table width), and
  the names wrap (`overflow-wrap: anywhere`; the team name only truncates from `sm` up). A
  `max-width` on the cell's content alone does not work: verified in headless Chromium at 360px,
  auto table layout still handed the table's spare width to the column (381px). With the
  cell width set, the column measured 268px for both long and short names and stayed pinned while
  scrolling. From `sm` up the column is `w-auto`, so desktop is unchanged.
