# FE-016: Instructions / Docs Page

## Description
The `/docs` page provides user-facing instructions for using LeagueQL: how to find your
ESPN/Sleeper league ID, how to retrieve ESPN cookies (including via the Chrome extension),
how onboarding/refresh work, how migration works, and how **ownership & access** work (the league
owner model, joining an ESPN league via membership verification, and transferring ownership —
see [FE-025](FE-025-ownership-transfer-owner-gated-actions.md) /
[BE-016](../backend/BE-016-league-ownership-authorization.md)). LeagueQL is entirely free.
Rendered with the marketing header (scrollable content area).

## Scope
- Route: `/docs` (public).
- Component: `src/features/instructions/instructions-page.tsx`.

## Edge Cases
- **Extension vs. manual cookie steps:** documents both paths
  ([EXT-001](../extension/EXT-001-espn-cookie-autofill.md), manual entry).
- **Platform differences:** ESPN vs. Sleeper steps differ (ESPN needs season + cookies for
  private leagues).
- **Long content:** content area scrolls independently with the header fixed. On large
  screens the table-of-contents sidebar and the instructions content are each their own
  scroll container (with scroll chaining contained), so the TOC can be scrolled without
  moving the instructions and vice versa.
- **Keeping in sync:** instructions must be updated when onboarding/migration flows change.
- **Ownership & access:** explains that the first connector is the owner; that owner-only
  actions (refresh, migrate, transfer ownership, delete) are
  hidden from non-owners; how a non-owner joins a private ESPN league via membership
  verification (extension cookies); and the one-time-token ownership-transfer/claim flow — kept
  consistent with [FE-025](FE-025-ownership-transfer-owner-gated-actions.md) /
  [BE-016](../backend/BE-016-league-ownership-authorization.md).

## Acceptance Criteria
- [ ] `/docs` renders user instructions for finding league IDs, retrieving ESPN cookies, and
      onboarding/refresh/migration.
- [ ] Connecting a League splits ESPN and Sleeper into their own subsections (each a
      table-of-contents entry); the ESPN subsection shows a screenshot of the Onboard/Refresh
      League form followed by a "Form Fields" sub-subsection (also a table-of-contents entry)
      documenting the League ID, Latest Season, SWID, and ESPN S2 fields, and a "Chrome
      Extension" sub-subsection (also a table-of-contents entry) describing the LeagueQL ESPN
      Cookie Helper extension ([EXT-001](../extension/EXT-001-espn-cookie-autofill.md)) that
      autofills the SWID/ESPN S2 cookies, with a link to its Chrome Web Store listing.
- [ ] Both extension-based and manual ESPN cookie retrieval are documented.
- [ ] Under Managing Your League, the "Refreshing League Data" subsection splits its ESPN and
      Sleeper instructions into their own sub-subsections, each a (level-3) table-of-contents
      entry. The Sleeper sub-subsection is further divided into "Midseason Refreshes" and "New
      Season Refreshes" labels that are not table-of-contents entries.
- [ ] Content scrolls within the page while the header remains.
- [ ] An Ownership & Access section documents the league-owner model and owner-only actions,
      joining a private ESPN league via membership verification (with a screenshot of the
      "Join league" / verify-membership dialog), and transferring ownership via a one-time
      token.

## Sources
`src/features/instructions/instructions-page.tsx`.
