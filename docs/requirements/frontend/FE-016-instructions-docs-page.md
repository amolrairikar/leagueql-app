# FE-016: Instructions / Docs Page

> **Billing content is feature-flagged ([FE-026](FE-026-feature-flags.md)).** The Subscribing,
> Free Trial, and Managing Billing sections (and their table-of-contents entries), the
> "Why is there a subscription for the app?" FAQ, and the inline billing mentions in the
> Ownership & Access and Navigation sections are shown only when the `billing` flag is ON. When
> OFF (the current default), all of that is hidden; the rest of the guide renders unchanged.

## Description
The `/docs` page provides user-facing instructions for using LeagueQL: how to find your
ESPN/Sleeper league ID, how to retrieve ESPN cookies (including via the Chrome extension),
how onboarding/refresh work, how migration works, how **ownership & access** work (the league
owner model, joining an ESPN league via membership verification, and transferring ownership —
see [FE-025](FE-025-ownership-transfer-owner-gated-actions.md) /
[BE-016](../backend/BE-016-league-ownership-authorization.md)), and how **billing &
subscriptions** work (Stripe checkout, the free trial, managing/canceling billing).
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
- **Keeping in sync:** instructions must be updated when onboarding/migration/billing flows
  change.
- **Billing details:** explains the per-league subscription, the once-per-league free trial,
  applying a promotion code at Stripe Checkout, and that cancellation (via the Stripe Billing
  Portal) takes effect immediately — kept consistent with
  [BE-015](../backend/BE-015-stripe-billing.md) /
  [FE-021](FE-021-subscription-access-control.md).
- **Ownership & access:** explains that the first connector is the owner; that owner-only
  actions (refresh, migrate, manage subscription/subscribe, transfer ownership, delete) are
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
- [ ] Content scrolls within the page while the header remains.
- [ ] The docs document how to subscribe (Stripe Checkout), the once-per-league free trial, and
      promotion codes (under Connecting a League), plus managing/canceling billing — immediate
      cancellation via the Stripe Billing Portal (under Managing Your League).
- [ ] An Ownership & Access section documents the league-owner model and owner-only actions,
      joining a private ESPN league via membership verification (with a screenshot of the
      "Join league" / verify-membership dialog), and transferring ownership via a one-time
      token.

## Sources
`src/features/instructions/instructions-page.tsx`.
