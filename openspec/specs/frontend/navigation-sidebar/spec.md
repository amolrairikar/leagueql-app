# navigation-sidebar Specification

## Purpose
The collapsible app sidebar and surrounding layout shared by all in-app pages. It provides navigation to every analytics feature, a refresh entry point for the current league, the demo-mode banner, and the account menu. The header shows the LeagueQL wordmark and theme toggle.

## Requirements

### Requirement: Navigate to all analytics pages
The sidebar SHALL link to all ten analytics pages and route to them correctly, with a header wordmark linking home and a theme toggle present.

#### Scenario: Navigation
- **WHEN** the user opens the sidebar
- **THEN** it links to Home, Standings, Matchups, Playoff Bracket, Manager Comparison, Manager History, Draft Recap, Draft Grades, Player Records, and Matchup Records, each routing correctly, with the header wordmark linking home and the theme toggle present

### Requirement: Refresh the current league
The sidebar SHALL expose a refresh action pre-filled and locked to the current league and surface the backend cooldown/up-to-date/in-progress responses.

#### Scenario: Sidebar refresh
- **WHEN** the user triggers the sidebar refresh
- **THEN** the form is pre-filled and locked to the currently-viewed league, and `429`/`409` cooldown/up-to-date/in-progress responses are surfaced

### Requirement: Responsive layout with reachable account menu
The layout SHALL be responsive (sidebar collapses/toggles on mobile), and the account menu (sign out) SHALL be reachable on both desktop (sidebar footer) and mobile (header), never inside the modal sidebar sheet.

#### Scenario: Mobile collapse
- **WHEN** the app is viewed on mobile
- **THEN** the sidebar collapses and toggles via `SidebarTrigger`

#### Scenario: Account menu placement
- **WHEN** the account menu is rendered
- **THEN** it appears in the sidebar footer on desktop and in the always-present header on mobile (not inside the modal sheet), so "Sign out" is reachable and functional

### Requirement: Demo banner and no marketing footer
The demo banner SHALL appear in demo mode, and the in-app layout SHALL NOT render the marketing footer.

#### Scenario: Demo banner
- **WHEN** demo mode is active
- **THEN** the demo banner appears on in-app pages

#### Scenario: No marketing footer
- **WHEN** an in-app page renders
- **THEN** the marketing footer (About / Privacy / GitHub) is not shown (it appears only on public pages)

### Requirement: Owner-gated sidebar actions
Owner-only actions SHALL be gated on `is_owner`, with non-owners seeing the alternate actions.

#### Scenario: Owner vs non-owner actions
- **WHEN** the sidebar renders for a league
- **THEN** Refresh, Migrate, Transfer Ownership, and Delete are shown only when `is_owner` is true, and non-owners see View Another League and Claim Ownership instead
