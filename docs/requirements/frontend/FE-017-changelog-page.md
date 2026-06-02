# FE-017: Changelog Page

## Description
The `/changelog` page presents a user-facing history of notable product changes and feature
releases. Rendered with the marketing header and footer.

## Scope
- Route: `/changelog` (public).
- Component: `src/features/changelog/changelog-page.tsx`.

## Edge Cases
- **Ordering:** entries listed newest-first.
- **Empty/initial state:** renders cleanly with no/few entries.
- **Maintenance:** changelog entries are added when user-visible features ship.

## Acceptance Criteria
- [ ] `/changelog` renders a chronological (newest-first) list of changelog entries.
- [ ] The page renders with the marketing header and footer.
- [ ] New user-visible features are reflected with a changelog entry.

## Sources
`src/features/changelog/changelog-page.tsx`.
