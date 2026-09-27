## Why

On narrow (mobile) viewports, a long owner username or team name in the matchup preview's hero
header cannot shrink below its longest unbroken word. The header grid then grows wider than the
card, and the card's `overflow-hidden` clips the names so they run off the screen with no way to
read them.

## What Changes

- Make each matchup preview card its own horizontal scroll container. When a card's minimum
  width (driven by long team/owner names) exceeds the viewport, only that card widens and scrolls
  sideways; cards whose content fits stay at the viewport width with no scrollbar or whitespace.
- Let the Recent Form card's usernames wrap so that card always fits the mobile viewport.
- The close button stays pinned to the preview's top-right corner outside every card, so it is
  neither clipped nor scrolled away.

## Capabilities

### New Capabilities
<!-- None -->

### Modified Capabilities
- `frontend/matchup-previews`: adds a requirement that overflowing preview content scrolls
  horizontally instead of being clipped.

## Impact

- Frontend: `frontend/src/features/matchups/matchup-preview.tsx` (`MatchupPreviewCard` layout).
- Tests: `frontend/src/features/matchups/__tests__/matchups.{feature,steps.test.tsx}`.
- No backend, API-contract, or extension changes.
