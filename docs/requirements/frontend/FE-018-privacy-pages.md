# FE-018: Privacy Pages

## Description
Public privacy policy pages: a general app privacy page (`/privacy`) and a dedicated privacy
page for the Chrome extension (`/extension-privacy`). The extension privacy page is required
for Chrome Web Store listing and explains how ESPN cookies are handled.

## Scope
- Routes: `/privacy`, `/extension-privacy` (public).
- Components: `src/features/privacy/privacy-page.tsx`,
  `src/features/privacy/extension-privacy-page.tsx`.

## Edge Cases
- **ESPN cookie handling disclosure:** the extension privacy page must state that ESPN
  cookies are read only for onboarding, transmitted once over HTTPS, and never stored/logged
  ([EXT-001](../extension/EXT-001-espn-cookie-autofill.md), [BE-001](../backend/BE-001-league-onboarding.md)).
- **Consistency with actual behavior:** privacy claims must match real data handling in the
  app and extension.
- **Accessible without auth:** both pages are public.

## Acceptance Criteria
- [ ] `/privacy` renders the general privacy policy publicly.
- [ ] `/extension-privacy` renders the extension-specific privacy policy publicly.
- [ ] The extension privacy page accurately describes ESPN cookie handling.
- [ ] Privacy statements stay consistent with actual data handling.

## Sources
`src/features/privacy/privacy-page.tsx`, `src/features/privacy/extension-privacy-page.tsx`.
