# Design

## Context

The comparison grid is `grid-cols-[1fr_110px_1fr]`. In CSS grid, a bare `1fr` is
`minmax(auto, 1fr)`, so a column can't shrink below its min-content. A long unbreakable username
in one header cell raises that column's minimum, and the grid gives it more of the fixed width.
The opposite column is squeezed.

## Decisions

- **Size the grid to its content and scroll the overflow.** The grid gets `w-max min-w-full`
  inside an `overflow-x-auto` wrapper. When a grid's width is its max-content, each `1fr` track
  resolves to the largest max-content among the flexible tracks. Both manager columns therefore
  come out equal to the wider one. When that fits, `min-w-full` stretches the grid to the
  container and the two `1fr` tracks split the space equally as before. When it doesn't fit, the
  wrapper scrolls horizontally.
- **Let the scroll container shrink.** On mobile the page grid is `grid-cols-1`, whose `1fr`
  track has the same `auto` minimum. The wrapped grid's intrinsic width would widen the whole
  column and the page instead of scrolling. The mobile track becomes `minmax(0,1fr)` and the
  left column gets `min-w-0`, so the overflow stays inside the wrapper.
- **Don't truncate or break names.** The request is for equal columns with scrolling, keeping the
  full username visible.

## Non-Goals

- The manager `<select>`s: both list the same options, so their widths are already equal.
- The loading skeleton, which has no usernames.
