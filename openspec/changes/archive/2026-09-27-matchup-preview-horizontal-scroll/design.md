## Context

`MatchupPreviewCard` renders a column of `Card`s (each `overflow-hidden`). The hero card's header
is a `grid-cols-[1fr_auto_1fr]` grid; `1fr` tracks have a min-content floor, so a long unbroken
username forces the grid wider than the card, and the card clips it.

## Decisions

- **Scroll per card, not the whole preview.** Each `Card` is `overflow-x-auto` with a `min-w-fit`
  (`min-width: fit-content`) inner wrapper: the content fills the card normally and only grows to
  its min-content width when that exceeds the viewport. An earlier iteration scrolled the whole
  column as one unit, but then a long name in the hero header stretched every card (e.g. Recent
  Form) to the same width, leaving scrollable whitespace.
- **Wrap Recent Form usernames.** The username in each Recent Form header uses
  `overflow-wrap: anywhere` (which, unlike `break-word`, lowers min-content width), so that card
  never needs to scroll.
- **Close button outside the cards.** It is absolutely positioned (`-top-3 -right-3`) against the
  outer `relative` wrapper, so no card's overflow clips it.
- Rejected: truncating names with an ellipsis — hides the very information the user wants to read.

## Risks

- Charts (`ResponsiveContainer`) resize to their card's width; a chart card only widens if its
  own content overflows.
