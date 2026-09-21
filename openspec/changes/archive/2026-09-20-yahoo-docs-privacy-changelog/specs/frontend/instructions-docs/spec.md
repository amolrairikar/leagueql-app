# Spec Delta

## MODIFIED Requirements

### Requirement: Document connecting a league
`/docs` SHALL render instructions for finding league IDs, retrieving ESPN cookies, and onboarding/refresh/migration, splitting ESPN, Sleeper, and Yahoo into their own table-of-contents subsections and documenting both extension and manual cookie retrieval. The Yahoo subsection SHALL document the OAuth connect flow — selecting Yahoo and entering the league ID, authorizing LeagueQL on Yahoo's consent screen, and onboarding resuming automatically on return — and SHALL note that an already-linked user connects in place without revisiting the consent screen.

#### Scenario: Connect instructions
- **WHEN** the docs page renders
- **THEN** Connecting a League splits ESPN, Sleeper, and Yahoo into their own TOC subsections, the ESPN subsection shows the Onboard/Refresh form screenshot plus a "Form Fields" sub-subsection (League ID, Latest Season, SWID, ESPN S2) and a "Chrome Extension" sub-subsection linking the Web Store listing, and both extension-based and manual ESPN cookie retrieval are documented

#### Scenario: Yahoo connect instructions
- **WHEN** the docs page renders
- **THEN** the Yahoo subsection documents the OAuth connect flow (select Yahoo and enter the league ID, authorize LeagueQL on Yahoo's consent screen, onboarding resumes automatically on return) and its league-ID form field, and notes that an already-linked user connects in place without revisiting the consent screen
