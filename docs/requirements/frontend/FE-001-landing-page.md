# FE-001: Landing Page

## Description
The public marketing/home page at `/`. Introduces LeagueQL, showcases the product with real
screenshots, highlights the feature set, explains how onboarding works, displays the live count
of onboarded leagues as social proof, and routes visitors to sign in / connect a league or enter
demo mode. LeagueQL is entirely free. Rendered with the marketing `Header` (not the app sidebar
layout).

The page reads top-to-bottom as: **hero** (social-proof count pill, headline, subhead, primary
"Connect Your League" + "View Demo" CTAs, and the revealed inline connect form) → **product
showcase** ("See it in action" — a swipeable scroll-snap carousel of product screenshots with
dot indicators, auto-advancing and wrapping around at either edge at every breakpoint)
→ **"Works with" strip** (ESPN + Sleeper logos) → **feature highlights** (lucide-icon cards) →
**"How it works"** (3 numbered steps) → **final CTA band** → marketing `Footer`. A fixed grid +
primary-glow backdrop and `fadeUp` hero entrance animations are decorative and honor
`prefers-reduced-motion`.

## Scope
- Route: `/` (`src/app/app.tsx`).
- Component: `src/features/landing_page/landing-page.tsx`; copy/links/data in `constants.ts`.
  Subcomponent: `product-showcase.tsx` (swipeable screenshot carousel).
- Counts fetch: `https://api.leagueql.com/counts` ([BE-013](../backend/BE-013-app-stats-league-count.md)).
- Product showcase: driven by `SLIDES` in `constants.ts` (Standings, Matchups, Playoff Bracket,
  Manager Comparison, Player Records, Draft Recap) using the screenshots in `src/assets/`.
- Feature highlights (`FEATURES`, lucide icons): Complete History, Rivalry Tracker, Championship
  Timeline, Team Trends, League Records, Platform Migration.
- "Works with" logos (`PLATFORMS`): ESPN + Sleeper marks from
  `src/assets/espn-logo.svg` and `src/assets/sleeper-logo.svg`.
- Nav links: Changelog (in-app `/changelog`, [FE-028](FE-028-changelog-page.md)), Docs (`/docs`).

## Edge Cases
- **Counts endpoint fails/slow:** the league-count figure degrades gracefully (placeholder
  or hidden), never blocking the page.
- **Signed-in user:** primary CTA should route into the app rather than re-prompting sign in.
- **Demo mode entry:** offers a way to explore with sample data without connecting a league.
- **Inline connect routing:** the inline connect form resolves the league via `getLeague`. A
  Sleeper `404` onboards in place; an ESPN `404` (not onboarded) routes to `/connect_league` to
  onboard. An ESPN `403` (already onboarded but the caller isn't a member of the private league
  yet) opens the **Join League** dialog (membership verification) in place rather than the
  onboard form (LQL-01 / BE-016 / FE-025). Other failures show a generic inline message.
- **Mobile layout:** feature grid and hero must remain legible on small screens. In the
  "Works with" strip, the "Works with" label sits on its own line (full width) with the
  platform chips wrapping below it on mobile; the label returns inline with the chips at `sm`
  and up.

## Acceptance Criteria
- [ ] `/` renders the hero, product showcase, "Works with" strip, feature highlights, "How it
      works" steps, final CTA band, and footer with the marketing header.
- [ ] The product showcase renders product screenshots in a swipeable scroll-snap carousel with
      dot indicators, auto-advancing (pausing on pointer interaction; disabled under
      `prefers-reduced-motion`).
- [ ] The carousel wraps around: swiping past the last slide loops to the first, and swiping
      back from the first loops to the last (seamless in both directions).
- [ ] The live onboarded-league count is shown when the counts endpoint responds, and the
      page still renders (count pill hidden) if it fails.
- [ ] CTAs route to sign in / connect league (or into the app for signed-in users) and to
      demo mode.
- [ ] The Docs nav link resolves to `/docs`; the Changelog nav link resolves to the in-app
      `/changelog` page ([FE-028](FE-028-changelog-page.md)).
- [ ] Layout is responsive on mobile and desktop.

## Sources
`src/features/landing_page/landing-page.tsx`, `product-showcase.tsx`, `constants.ts`,
`types.ts`, `src/app/app.tsx`.
