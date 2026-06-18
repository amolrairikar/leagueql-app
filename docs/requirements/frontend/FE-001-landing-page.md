# FE-001: Landing Page

## Description
The public marketing/home page at `/`. Introduces LeagueQL, showcases the feature set,
displays the live count of onboarded leagues as social proof, presents a pricing table for the
premium subscription, and routes visitors to sign in / connect a league or enter demo mode.
Rendered with the marketing `Header` (not the app sidebar layout).

## Scope
- Route: `/` (`src/app/app.tsx`).
- Component: `src/features/landing_page/landing-page.tsx`; copy/links in `constants.ts`.
- Counts fetch: `https://api.leagueql.com/counts` ([BE-013](../backend/BE-013-app-stats-league-count.md)).
- Feature highlights: Standings, Matchups, Playoff Bracket, Manager Comparison, Manager
  History, Draft Grades, Player Records, Matchup Records, Complete History, Rivalry Tracker,
  Championship Timeline, Team Trends, League Records, Platform Migration.
- Pricing table: `src/features/landing_page/pricing-table.tsx`, rendered below the feature grid.
  Shows two subscription plans — **Monthly $2.99/month** and **Yearly $14.99/year** (the yearly
  plan is highlighted as the best value, ~58% cheaper than 12 monthly payments) — notes that all
  subscriptions come with a 14-day trial, and lists the **premium features** a subscription
  unlocks (the **Schedule-swap simulator**, [FE-031](FE-031-schedule-swap-simulator.md), and
  **Weekly awards**, [FE-032](FE-032-weekly-awards-superlatives.md)). Plans
  and premium features come from `PRICING_PLANS` / `PREMIUM_FEATURES` in `constants.ts`. The table
  is **informational** — there is no per-plan CTA (checkout needs a connected league), and the
  blurb notes a subscription is shared across the whole league (every member gets access) and that
  you select a subscription after connecting your league; the plan is chosen in-app via
  the Subscribe flow's toggle ([FE-022](FE-022-subscription-checkout.md)). The whole table is
  feature-flagged on `billing` ([FE-026](FE-026-feature-flags.md)): it is hidden when billing is
  OFF (premium features are free then, so there is nothing to sell).
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
- **Mobile layout:** feature grid, hero, and pricing table must remain legible on small screens
  (plans stack vertically).
- **Billing flag OFF:** the pricing table is not rendered (premium features are free; FE-026).

## Acceptance Criteria
- [ ] `/` renders the hero, feature highlights, and footer with the marketing header.
- [ ] The live onboarded-league count is shown when the counts endpoint responds, and the
      page still renders if it fails.
- [ ] CTAs route to sign in / connect league (or into the app for signed-in users) and to
      demo mode.
- [ ] With `billing` ON, a pricing table below the feature grid shows the Monthly ($2.99/month) and
      Yearly ($14.99/year) plans and lists the premium features (the Schedule-swap simulator and
      Weekly awards), with no per-plan CTA; with `billing` OFF it is hidden.
- [ ] The Docs nav link resolves to `/docs`; the Changelog nav link resolves to the in-app
      `/changelog` page ([FE-028](FE-028-changelog-page.md)).
- [ ] Layout is responsive on mobile and desktop.

## Sources
`src/features/landing_page/landing-page.tsx`, `pricing-table.tsx`, `constants.ts`,
`src/app/app.tsx`.
