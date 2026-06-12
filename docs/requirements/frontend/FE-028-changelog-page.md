# FE-028: Changelog Page

## Description
A public, in-app changelog at `/changelog` listing notable releases newest-first. Each release
shows its version, date, and one or more sections (e.g. **Added**, **Changed**, **Fixed**) of
bullet items. A "Releases" sidebar (desktop) links to each version anchor. Rendered with the
marketing `Header` (not the app sidebar layout), matching the privacy pages
([FE-018](FE-018-privacy-pages.md)).

This replaces the previous Changelog nav link, which pointed at a `CHANGELOG.md` file on GitHub
([FE-001](FE-001-landing-page.md)); the Changelog nav link now resolves to `/changelog` in-app,
and the in-app content is the single source of truth (the standalone `CHANGELOG.md` was removed).

## Scope
- Route: `/changelog` (public) — `src/app/app.tsx`.
- Component: `src/features/changelog/changelog-page.tsx`.
- Content: `src/features/changelog/constants.ts` — a `CHANGELOG` array of releases
  (`{ version, date, sections: [{ title, items }] }`), newest first. This is the single source
  of truth for the changelog; a new release is added here when it ships.
- Nav link: `Changelog` in `NAV_LINKS` (`src/features/landing_page/constants.ts`) is internal
  (`href: '/changelog'`, `external: false`).

## Edge Cases
- **Accessible without auth:** the page is public (no connected league required).
- **Anchor scrolling:** version ids are derived from the version (e.g. `1.1.0` → `v1-1-0`); the
  sidebar buttons smooth-scroll to each release, with `scroll-mt` offset for the sticky header.
- **Mobile layout:** the "Releases" sidebar is hidden on small screens; the release list remains
  legible.

## Acceptance Criteria
- [ ] `/changelog` renders publicly with the marketing header and a "Changelog" heading.
- [ ] Each release renders its version, date, and section bullet items, newest version first.
- [ ] The Changelog nav link resolves to `/changelog` in-app (no longer opens GitHub).

## Sources
`src/features/changelog/changelog-page.tsx`, `src/features/changelog/constants.ts`,
`src/app/app.tsx`, `src/features/landing_page/constants.ts`,
[FE-001](FE-001-landing-page.md) (nav link).
