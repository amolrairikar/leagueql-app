# Spec Delta

## MODIFIED Requirements

### Requirement: Document connecting a league
`/docs` SHALL render instructions for finding league IDs, retrieving ESPN cookies, and onboarding/refresh/migration, splitting ESPN, Sleeper, and Yahoo into their own table-of-contents subsections and documenting both extension and manual cookie retrieval. The ESPN subsection SHALL state that stored ESPN cookies are shared by all of the user's ESPN leagues and are removed once none of those leagues has automatic refresh on. The Yahoo subsection SHALL document the OAuth connect flow — selecting Yahoo and entering the league ID, authorizing LeagueQL on Yahoo's consent screen, and onboarding resuming automatically on return — and SHALL note that an already-linked user connects in place without revisiting the consent screen.

#### Scenario: Connect instructions
- **WHEN** the docs page renders
- **THEN** Connecting a League splits ESPN, Sleeper, and Yahoo into their own TOC subsections, the ESPN subsection shows a "Form Fields" sub-subsection (League ID, SWID, ESPN S2) and a "Chrome Extension" sub-subsection linking the Web Store listing, and both extension-based and manual ESPN cookie retrieval are documented

#### Scenario: Shared ESPN cookie removal documented
- **WHEN** the ESPN connect subsection describes cookie storage
- **THEN** it states that stored cookies are shared by all of the user's ESPN leagues and removed once none of them has automatic refresh on, rather than when any single league is turned off or deleted

#### Scenario: Yahoo connect instructions
- **WHEN** the docs page renders
- **THEN** the Yahoo subsection documents the OAuth connect flow (select Yahoo and enter the league ID, authorize LeagueQL on Yahoo's consent screen, onboarding resumes automatically on return) and its league-ID form field, and notes that an already-linked user connects in place without revisiting the consent screen

### Requirement: Document managing a league with always-on Yahoo refresh

`/docs` SHALL document refreshing under a "Managing Your League" section that splits ESPN, Sleeper,
and Yahoo refresh into their own level-3 TOC sub-subsections, with the Sleeper one divided into
Midseason and New Season labels. The ESPN sub-subsection SHALL document that automatic weekly
in-season refresh is opt-in per league — enabled via the auto-refresh checkbox on the connect form
or the Refresh League dialog — that enabling it stores the ESPN cookies encrypted and those cookies
can expire and occasionally need re-entering, that an ESPN owner can turn auto-refresh off from the
sidebar's Turn Off Auto-Refresh action (which removes the stored cookies once no other ESPN league
of theirs has auto-refresh on), and that manual refresh via the sidebar's Refresh League action
remains available for ESPN leagues, limited to once per week per league and only during the season
when newer data exists. The Yahoo sub-subsection SHALL document that Yahoo leagues refresh
automatically each week during the season using the connected Yahoo account, with nothing to enable
and no manual refresh action.

#### Scenario: Refresh instructions

- **WHEN** the Managing Your League section renders
- **THEN** the "Refreshing League Data" subsection splits ESPN, Sleeper, and Yahoo into their own
  level-3 TOC entries, and the Sleeper sub-subsection is further divided into "Midseason Refreshes"
  and "New Season Refreshes" labels (not TOC entries)

#### Scenario: ESPN opt-in auto-refresh documented

- **WHEN** the ESPN refresh sub-subsection renders
- **THEN** it explains that automatic weekly in-season refresh is opt-in per league (enabled via the
  connect-form checkbox or the Refresh League dialog), that enabling it stores the ESPN cookies
  encrypted and cookies can expire and need re-entering, that the owner can turn auto-refresh off
  from the sidebar's Turn Off Auto-Refresh action (which removes the stored cookies once no other
  ESPN league of theirs has auto-refresh on), and that manual refresh via the sidebar's Refresh
  League action remains available

#### Scenario: Manual refresh limits documented

- **WHEN** the ESPN refresh sub-subsection describes manual refresh
- **THEN** it states that a league can be refreshed manually at most once per week, and not during
  the offseason or when the league is already up to date

#### Scenario: Yahoo always-on auto-refresh documented

- **WHEN** the Yahoo refresh sub-subsection renders
- **THEN** it explains that Yahoo leagues refresh automatically each week during the season using the
  connected Yahoo account, with no opt-in to enable, and does not describe an opt-in checkbox or a
  manual refresh action
