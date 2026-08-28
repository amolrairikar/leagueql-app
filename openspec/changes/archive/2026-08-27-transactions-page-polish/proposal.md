# Transactions page polish

## Why
The `/transactions` type filter currently offers **All / Trades / Waivers / Free Agents** and
defaults to **All**. Trades are the transactions managers most want to revisit, and the "All"
view mixes high-signal trades in with a long tail of routine waiver/free-agent churn. Defaulting
to **Trades** (and dropping "All") puts the most interesting activity first. Alongside this
behavior change, the page's hand-rolled markup is being restyled for a cleaner, more polished
look (segmented filter control, color-accented type chips, refined transaction cards and summary
table) — visual only, no requirement impact beyond the filter set.

## What Changes
- **Type filter set:** remove the **All** option; the filter offers **Trades / Waivers /
  Free Agents** only.
- **Default filter:** the page loads with **Trades** selected instead of All.
- **Visual restyle (no behavior change):** segmented filter control with per-type icons,
  per-type color-accented chips, restyled transaction cards and per-owner summary table. The
  data shown, empty/error states, summary counts, and avatar reuse are unchanged.

## Impact
- Affected specs: `frontend/transactions` (Requirement: Season selector and type filter).
- Affected code: `frontend/src/features/transactions/transactions.tsx` and its component tests
  under `frontend/src/features/transactions/__tests__/`.
