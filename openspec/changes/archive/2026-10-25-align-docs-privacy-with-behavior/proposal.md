# Proposal

## Why

An audit comparing the User Guide (`/docs`), the landing-page FAQ, the Privacy Policy
(`/privacy`), and the Extension Privacy Policy (`/extension-privacy`) against each other and
against the code turned up a set of inaccuracies and omissions:

- **ESPN cookie removal is overstated.** Stored ESPN cookies live in one per-user item shared by
  all of that user's ESPN leagues, and are removed only once the user has no other ESPN league with
  auto-refresh on. The User Guide and FAQ say they are removed when auto-refresh is turned off or
  "the league" is deleted.
- **Yahoo token removal is overstated.** The Privacy Policy says Yahoo tokens are removed when
  league data deletion is requested; they are actually removed only when the user's last Yahoo
  league is deleted (the Yahoo link is account-level).
- **Manual refresh is not "anytime".** The backend allows one refresh per league per week, and
  blocks refreshes during the offseason or when the league is already current. The FAQ promises
  "anytime" and neither page mentions the limits.
- **Wrong autofill button label.** The FAQ and Extension Privacy Policy say "Autofill from ESPN";
  the button reads "Autofill cookies from ESPN".
- **Undisclosed processor.** Frontend and backend traces (including the signed-in account ID,
  route paths, Web Vitals, and errors) go to Better Stack, which the Privacy Policy does not list.
- **Undisclosed stored data.** League membership/invite records, ownership-transfer tokens, the
  My Team claim, and Google sign-in through Clerk are not mentioned.
- **Deletion rights don't match the product.** Deletion is a self-serve, owner-only Delete League
  action; the policy says nothing about how non-owners or account holders remove their data.
- **Stale copy.** Both privacy pages' "Last updated" dates predate content they contain; the site
  meta description and JSON-LD omit Yahoo; the ESPN "Form Fields" heading reads "Fields"; and the
  FAQ claims all ESPN leagues are private.

## What Changes

- **Privacy Policy:** correct the Yahoo token removal statement; add a "Usage & diagnostics"
  disclosure and list Better Stack under Third-Party Services; disclose membership, ownership,
  and My Team data and Google sign-in; rewrite "Your Rights" to describe owner self-serve
  deletion and email-based removal for everyone else; bump "Last updated".
- **Extension Privacy Policy:** use the real "Autofill cookies from ESPN" label and bump
  "Last updated".
- **User Guide:** say stored ESPN cookies are shared across the user's ESPN leagues and removed
  once no ESPN league of theirs has auto-refresh on; document the once-per-week / in-season
  manual refresh limits; fix the "Form Fields" heading.
- **FAQ:** correct the cookie-removal statement, the private-league claim, the autofill label,
  and the "anytime" manual refresh wording.
- **`index.html`:** include Yahoo in the meta description and JSON-LD description.
- **Specs:** fix the drift in `frontend/instructions-docs` (no form screenshot or Latest Season
  field on the ESPN connect form) alongside the behavioral corrections.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `frontend/privacy-pages`: accurate Yahoo/ESPN credential removal, diagnostics/processor
  disclosure, account-linked data disclosure, and deletion-rights description.
- `frontend/instructions-docs`: accurate ESPN connect form fields, shared-cookie removal, and
  manual refresh limits.
- `frontend/landing-page`: FAQ answers match actual credential handling, refresh limits, and UI
  labels.

## Impact

- Frontend copy only:
  - `frontend/src/features/privacy/privacy-page.tsx`
  - `frontend/src/features/privacy/extension-privacy-page.tsx`
  - `frontend/src/features/instructions/instructions-page.tsx`
  - `frontend/src/features/landing_page/faq.tsx`
  - `frontend/index.html`
  - `frontend/src/features/landing_page/__tests__/static-pages.{feature,steps.test.tsx}`
- No backend, API-contract, DynamoDB, or infrastructure changes.
