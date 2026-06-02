# FE-001: Landing Page

## Description
The public marketing/home page at `/`. Introduces LeagueQL, showcases the feature set,
displays the live count of onboarded leagues as social proof, and routes visitors to sign
in / connect a league or enter demo mode. Rendered with the marketing `Header` (not the app
sidebar layout).

## Scope
- Route: `/` (`src/app/app.tsx`).
- Component: `src/features/landing_page/landing-page.tsx`; copy/links in `constants.ts`.
- Counts fetch: `https://api.leagueql.com/counts` ([BE-013](../backend/BE-013-app-stats-league-count.md)).
- Feature highlights: Standings, Matchups, Playoff Bracket, Manager Comparison, Manager
  History, Draft Grades, Player Records, Matchup Records, Complete History, Rivalry Tracker,
  Championship Timeline, Team Trends, League Records, Platform Migration.
- Nav links: Changelog (`/changelog`), Docs (`/docs`).

## Edge Cases
- **Counts endpoint fails/slow:** the league-count figure degrades gracefully (placeholder
  or hidden), never blocking the page.
- **Signed-in user:** primary CTA should route into the app rather than re-prompting sign in.
- **Demo mode entry:** offers a way to explore with sample data without connecting a league.
- **Mobile layout:** feature grid and hero must remain legible on small screens.

## Acceptance Criteria
- [ ] `/` renders the hero, feature highlights, and footer with the marketing header.
- [ ] The live onboarded-league count is shown when the counts endpoint responds, and the
      page still renders if it fails.
- [ ] CTAs route to sign in / connect league (or into the app for signed-in users) and to
      demo mode.
- [ ] Changelog and Docs nav links resolve to `/changelog` and `/docs`.
- [ ] Layout is responsive on mobile and desktop.

## Sources
`src/features/landing_page/landing-page.tsx`, `constants.ts`, `src/app/app.tsx`.
