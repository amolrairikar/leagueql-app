# FE-016: Instructions / Docs Page

## Description
The `/docs` page provides user-facing instructions for using LeagueQL: how to find your
ESPN/Sleeper league ID, how to retrieve ESPN cookies (including via the Chrome extension),
how onboarding/refresh work, and how migration works. Rendered with the marketing header and
footer (scrollable content area).

## Scope
- Route: `/docs` (public).
- Component: `src/features/instructions/instructions-page.tsx`.

## Edge Cases
- **Extension vs. manual cookie steps:** documents both paths
  ([EXT-001](../extension/EXT-001-espn-cookie-autofill.md), manual entry).
- **Platform differences:** ESPN vs. Sleeper steps differ (ESPN needs season + cookies for
  private leagues).
- **Long content:** content area scrolls independently with header/footer fixed.
- **Keeping in sync:** instructions must be updated when onboarding/migration flows change.

## Acceptance Criteria
- [ ] `/docs` renders user instructions for finding league IDs, retrieving ESPN cookies, and
      onboarding/refresh/migration.
- [ ] Both extension-based and manual ESPN cookie retrieval are documented.
- [ ] Content scrolls within the page while header/footer remain.

## Sources
`src/features/instructions/instructions-page.tsx`.
