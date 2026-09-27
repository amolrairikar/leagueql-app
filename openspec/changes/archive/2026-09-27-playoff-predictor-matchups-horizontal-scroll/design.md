## Decisions

- **Scroll the matchups card.** The card becomes `overflow-x-auto` so overflowing rows scroll
  instead of being clipped.
- **Size the row column at max-content, floored at the card width (`w-max min-w-full`).** Each
  row is a `1fr 40px 1fr` grid. Under max-content sizing the grid algorithm resolves each `1fr` to
  the largest team card's max-content width, so both sides of a row are equal; the shared column
  then takes the widest row, and at that width every row's `1fr` tracks split evenly, so all team
  cards across the week are equal. `min-w-full` keeps the desktop layout (rows fill the card).
- Rejected: `min-w-fit` (min-content floor, used on the matchup preview cards). Verified in
  headless Chromium at 360px: it scrolls, but `1fr` tracks keep content-based minimums, so a long
  name's card came out 275px against 152px for its opponent. With `w-max min-w-full` all four
  cards measured 284px on mobile and 543px on desktop, unchanged from before.
- Rejected: fixing the `truncate` so names ellipsize, which would hide the names the user needs
  to pick between.
