# Design

## Placement

`AppLayout` wraps every in-app route in `SidebarInset` (`h-svh overflow-hidden`). Each page
scrolls inside its own `flex-1 overflow-auto` container. Rendering the footer as a `shrink-0`
last child of `SidebarInset`, after the `ErrorBoundary`, pins it to the bottom of every in-app
page without touching individual pages. That satisfies "the footer of each page where Yahoo
Fantasy Information is displayed".

## Gating

The component reads `getLeagueCookies()` / `isDemoMode()` and renders only when a league is
active, its platform is `YAHOO`, and demo mode is off, following the platform-gated banner pattern
(`sleeper-stale-season-banner.tsx`). Pages outside `AppLayout` (landing, docs, privacy, connect)
don't show league data from Yahoo's API, so they're out of scope.

## Logo legibility

Yahoo's brand rules forbid recoloring, inverting, or adding effects. The logo has black "fantasy"
text that disappears on the dark theme, so it sits on a small white rounded chip in every theme.
The logo stays unmodified and readable.

## Link

`https://sports.yahoo.com/fantasy/` is an official Yahoo Fantasy page. It opens with
`target="_blank"` and `rel="noopener noreferrer"`, like other outbound links.
