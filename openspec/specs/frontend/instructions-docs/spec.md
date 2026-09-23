# instructions-docs Specification

## Purpose
The public `/docs` page provides user-facing instructions for using LeagueQL: how to find your ESPN/Sleeper league ID, how to retrieve ESPN cookies (including via the Chrome extension), how onboarding/refresh/migration work, and how ownership & access work. Rendered with the marketing header and a scrollable content area.

## Requirements

### Requirement: Document connecting a league
`/docs` SHALL render instructions for finding league IDs, retrieving ESPN cookies, and onboarding/refresh/migration, splitting ESPN, Sleeper, and Yahoo into their own table-of-contents subsections and documenting both extension and manual cookie retrieval. The Yahoo subsection SHALL document the OAuth connect flow — selecting Yahoo and entering the league ID, authorizing LeagueQL on Yahoo's consent screen, and onboarding resuming automatically on return — and SHALL note that an already-linked user connects in place without revisiting the consent screen.

#### Scenario: Connect instructions
- **WHEN** the docs page renders
- **THEN** Connecting a League splits ESPN, Sleeper, and Yahoo into their own TOC subsections, the ESPN subsection shows the Onboard/Refresh form screenshot plus a "Form Fields" sub-subsection (League ID, Latest Season, SWID, ESPN S2) and a "Chrome Extension" sub-subsection linking the Web Store listing, and both extension-based and manual ESPN cookie retrieval are documented

#### Scenario: Yahoo connect instructions
- **WHEN** the docs page renders
- **THEN** the Yahoo subsection documents the OAuth connect flow (select Yahoo and enter the league ID, authorize LeagueQL on Yahoo's consent screen, onboarding resumes automatically on return) and its league-ID form field, and notes that an already-linked user connects in place without revisiting the consent screen

### Requirement: Document managing a league

`/docs` SHALL document refreshing under a "Managing Your League" section that splits ESPN, Sleeper,
and Yahoo refresh into their own level-3 TOC sub-subsections, with the Sleeper one divided into
Midseason and New Season labels. The ESPN and Yahoo sub-subsections SHALL document that automatic
weekly in-season refresh is opt-in per league — enabled via the auto-refresh checkbox on the connect
form (ESPN/Yahoo) or the sidebar auto-refresh toggle — that enabling ESPN auto-refresh stores the
ESPN cookies encrypted and those cookies can expire and occasionally need re-entering, and that
manual refresh remains available.

#### Scenario: Refresh instructions

- **WHEN** the Managing Your League section renders
- **THEN** the "Refreshing League Data" subsection splits ESPN, Sleeper, and Yahoo into their own
  level-3 TOC entries, and the Sleeper sub-subsection is further divided into "Midseason Refreshes"
  and "New Season Refreshes" labels (not TOC entries)

#### Scenario: Opt-in auto-refresh documented

- **WHEN** the ESPN and Yahoo refresh sub-subsections render
- **THEN** they explain that automatic weekly in-season refresh is opt-in per league (via the
  connect-form checkbox or the sidebar toggle), that enabling ESPN auto-refresh stores the ESPN
  cookies encrypted and cookies can expire and need re-entering, and that manual refresh remains
  available

### Requirement: Document ownership & access
`/docs` SHALL include an Ownership & Access section covering the owner model, joining a private ESPN league via membership verification, and one-time-token ownership transfer, and its owner-actions list SHALL mark the actions that are available only for ESPN leagues (Refresh League, Invite Leaguemates) as ESPN only.

#### Scenario: Ownership instructions
- **WHEN** the Ownership & Access section renders
- **THEN** it documents the first-connector-is-owner model, that owner-only actions are hidden from non-owners, how a non-owner joins a private ESPN league via membership verification (with the "Join league" dialog screenshot), and the one-time-token ownership transfer/claim flow

#### Scenario: ESPN-only owner actions labeled
- **WHEN** the owner-actions list renders
- **THEN** the Refresh League and Invite Leaguemates entries are labeled as ESPN only

### Requirement: Scrollable content with fixed header
The content SHALL scroll within the page while the header remains, with independent TOC and content scroll containers on large screens.

#### Scenario: Scrolling
- **WHEN** the docs page is scrolled on a large screen
- **THEN** the content scrolls with the header fixed, and the TOC sidebar and content are each their own scroll container with scroll chaining contained
