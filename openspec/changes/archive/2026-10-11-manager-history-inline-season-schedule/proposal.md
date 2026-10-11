# Proposal

## Why

On `/manager_history`, clicking a season card opens a modal dialog with that season's schedule. A modal hides the
rest of the page and allows only one season at a time. Letting each season card expand in place keeps the manager's
history visible and lets users compare seasons.

## What Changes

- Each season card on `/manager_history` becomes an inline expander. Clicking it toggles a panel under the card that
  shows the week-by-week schedule and results. No dialog opens.
- Several seasons can be expanded at once.
- Clicking a game in an expanded season shows its box score inside that card: beside the schedule on wide screens,
  stacked below it on narrow ones.
- A season with no played games is not expandable.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `frontend/manager-history`: adds the inline season-expander requirement.

## Impact

- **Frontend**: `frontend/src/features/manager_history/manager-history.tsx` (the dialog is replaced by an expandable
  `SeasonCard` and a `SeasonSchedulePanel`); component tests under `__tests__/`.
- No backend, API, or data-model changes.
