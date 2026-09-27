## ADDED Requirements

### Requirement: Document managing a league with always-on Yahoo refresh

`/docs` SHALL document refreshing under a "Managing Your League" section that splits ESPN, Sleeper,
and Yahoo refresh into their own level-3 TOC sub-subsections, with the Sleeper one divided into
Midseason and New Season labels. The ESPN sub-subsection SHALL document that automatic weekly
in-season refresh is opt-in per league — enabled via the auto-refresh checkbox on the connect form —
that enabling it stores the ESPN cookies encrypted and those cookies can
expire and occasionally need re-entering, that an ESPN owner can turn auto-refresh off from the
sidebar's Turn Off Auto-Refresh action (which removes the stored cookies), and that manual refresh
via the sidebar's Refresh League action remains available for ESPN leagues. The Yahoo
sub-subsection SHALL document that Yahoo leagues refresh automatically each week during the season
using the connected Yahoo account, with nothing to enable and no manual refresh action.

#### Scenario: Refresh instructions

- **WHEN** the Managing Your League section renders
- **THEN** the "Refreshing League Data" subsection splits ESPN, Sleeper, and Yahoo into their own
  level-3 TOC entries, and the Sleeper sub-subsection is further divided into "Midseason Refreshes"
  and "New Season Refreshes" labels (not TOC entries)

#### Scenario: ESPN opt-in auto-refresh documented

- **WHEN** the ESPN refresh sub-subsection renders
- **THEN** it explains that automatic weekly in-season refresh is opt-in per league (enabled via the
  connect-form checkbox), that enabling it stores the ESPN cookies encrypted and cookies can expire and need
  re-entering, that the owner can turn auto-refresh off from the sidebar's Turn Off Auto-Refresh
  action (which removes the stored cookies), and that manual refresh via the sidebar's Refresh
  League action remains available

#### Scenario: Yahoo always-on auto-refresh documented

- **WHEN** the Yahoo refresh sub-subsection renders
- **THEN** it explains that Yahoo leagues refresh automatically each week during the season using the
  connected Yahoo account, with no opt-in to enable, and does not describe an opt-in checkbox or a
  manual refresh action

## REMOVED Requirements

### Requirement: Document managing a league

**Reason**: The Yahoo refresh docs no longer describe an opt-in; replaced by "Document managing a league with always-on Yahoo refresh", which keeps the section layout and ESPN content unchanged.

**Migration**: None. Docs copy only.
