# Design

## Expander

- Each season card is a `SeasonCard` with its own `open` state. The cards are keyed by manager + season, so switching
  managers collapses every card.
- The header is a `<button aria-expanded aria-controls>` with a rotating `ChevronDown`. This follows the existing
  draft-grades pattern rather than the FAQ-styled `Accordion` primitive. The button is disabled, and shows no
  chevron, when the season has no played games.
- The expanded body is a `role="region"` labelled by the header. It is only mounted while open, so the selected game
  resets when the card collapses.

## Schedule panel

- `SeasonSchedulePanel` keeps the dialog's table, its postseason divider, and its row-click box score. The `md+`
  layout is schedule on the left and `BoxScoreCard` on the right; on mobile the box score stacks below and scrolls
  into view.
- The dialog's inner max-height scroll and sticky header are removed because the page itself scrolls.
