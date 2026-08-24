# changelog Specification

## Purpose
A public, in-app changelog at `/changelog` listing notable releases newest-first. Each release shows its version, date, and one or more sections (Added, Changed, Fixed) of bullet items, with a desktop "Releases" sidebar linking to each version anchor. Rendered with the marketing header. The in-app content is the single source of truth (the standalone `CHANGELOG.md` was removed).

## Requirements

### Requirement: Render the changelog publicly
`/changelog` SHALL render publicly with the marketing header and a "Changelog" heading, showing each release's version, date, and section bullet items newest-first.

#### Scenario: Changelog render
- **WHEN** a visitor opens `/changelog` (no auth or connected league required)
- **THEN** it renders with the marketing header, a "Changelog" heading, and each release's version, date, and section bullet items, newest version first

### Requirement: In-app changelog nav link
The Changelog nav link SHALL resolve to `/changelog` in-app rather than opening GitHub.

#### Scenario: Nav link
- **WHEN** the Changelog nav link is used
- **THEN** it navigates to the in-app `/changelog` page

### Requirement: Anchor navigation
The desktop "Releases" sidebar SHALL smooth-scroll to each release anchor with a sticky-header offset, and the release list SHALL remain legible on mobile.

#### Scenario: Anchor scroll
- **WHEN** a "Releases" sidebar button is activated on desktop
- **THEN** it smooth-scrolls to the release's version id (e.g. `1.1.0` → `v1-1-0`) with `scroll-mt` offset

#### Scenario: Mobile layout
- **WHEN** the page is viewed on a small screen
- **THEN** the "Releases" sidebar is hidden and the release list remains legible
