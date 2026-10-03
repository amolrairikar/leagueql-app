# Proposal

## Why

Yahoo's Fantasy Sports API terms require clear attribution wherever Yahoo Fantasy data is shown.
On the web, the attribution has to sit in the footer of each page that displays the data, read
"Fantasy data provided by Yahoo Fantasy", link back to Yahoo Fantasy, and include the official,
unmodified Yahoo Fantasy logo (https://sports.yahoo.com/developer/). Today the in-app pages have
no footer at all, so Yahoo leagues are shown without the required attribution.

## What Changes

- New attribution footer at the bottom of the shared in-app layout (every `AppLayout` route:
  `/home`, `/standings`, `/matchups`, …). It shows the official Yahoo Fantasy logo and the text
  "Fantasy data provided by Yahoo Fantasy", and links to `https://sports.yahoo.com/fantasy/` in a
  new tab.
- The footer appears only when the active league's platform is Yahoo. It never appears for ESPN
  or Sleeper leagues, or in demo mode.
- New asset `frontend/src/assets/yahoo-fantasy-logo.svg`: the official logo, with its viewBox
  trimmed to the logo's own clip rect (only empty canvas removed; paths, colors and proportions
  unchanged).
- No **BREAKING** changes.

## Capabilities

### New Capabilities
- `frontend/yahoo-attribution`: the Yahoo-only attribution footer on in-app pages.

### Modified Capabilities
- None.

## Impact

- **Frontend:** `frontend/src/features/sidebar/yahoo-attribution-footer.tsx` (new),
  `frontend/src/app/app.tsx` (render it in `AppLayout`), `frontend/src/assets/yahoo-fantasy-logo.svg`
  (new), plus jest-cucumber tests under `frontend/src/features/sidebar/__tests__/`.
- No backend, infra, or API changes.
