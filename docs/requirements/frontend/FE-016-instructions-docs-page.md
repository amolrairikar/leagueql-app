# FE-016: Instructions / Docs Page

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
- [ ] Both extension-based and manual ESPN cookie retrieval are documented.
- [ ] Content scrolls within the page while the header remains.
- [ ] A Billing & Subscriptions section documents how to subscribe (Stripe Checkout), the
      once-per-league free trial, promotion codes, and managing/canceling billing (immediate
      cancellation via the Stripe Billing Portal).
- [ ] An Ownership & Access section documents the league-owner model and owner-only actions,
      joining a private ESPN league via membership verification, and transferring ownership via
      a one-time token.

## Sources
`src/features/instructions/instructions-page.tsx`.
