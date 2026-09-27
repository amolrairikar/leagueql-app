## Decisions

- The Top Scorers grid becomes `grid-cols-1 sm:grid-cols-2`. The right-hand column's existing
  `sm:` left padding stays for wide screens; on mobile it gets a top border and spacing instead,
  so the stacked lists read as two groups. This matches the breakpoint the preview already uses
  for the Head to head / Recent form row.
