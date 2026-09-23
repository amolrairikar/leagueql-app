## MODIFIED Requirements

### Requirement: Document managing a league

`/docs` SHALL document refreshing under a "Managing Your League" section that splits ESPN, Sleeper,
and Yahoo refresh into their own level-3 TOC sub-subsections, with the Sleeper one divided into
Midseason and New Season labels. The ESPN and Yahoo sub-subsections SHALL document that automatic
weekly in-season refresh is opt-in per league — enabled via the auto-refresh checkbox on the connect
form (ESPN/Yahoo) — that enabling ESPN auto-refresh stores the ESPN cookies encrypted and those
cookies can expire and occasionally need re-entering, that an ESPN owner can turn auto-refresh off
from the sidebar's Turn Off Auto-Refresh action (which removes the stored cookies), and that manual
refresh remains available.

#### Scenario: Refresh instructions

- **WHEN** the Managing Your League section renders
- **THEN** the "Refreshing League Data" subsection splits ESPN, Sleeper, and Yahoo into their own
  level-3 TOC entries, and the Sleeper sub-subsection is further divided into "Midseason Refreshes"
  and "New Season Refreshes" labels (not TOC entries)

#### Scenario: Opt-in auto-refresh documented

- **WHEN** the ESPN and Yahoo refresh sub-subsections render
- **THEN** they explain that automatic weekly in-season refresh is opt-in per league (enabled via the
  connect-form checkbox), that enabling ESPN auto-refresh stores the ESPN cookies encrypted and
  cookies can expire and need re-entering, that an ESPN owner can turn auto-refresh off from the
  sidebar's Turn Off Auto-Refresh action (which removes the stored cookies), and that manual refresh
  remains available

### Requirement: Document ownership & access
`/docs` SHALL include an Ownership & Access section covering the owner model, joining a private ESPN league via membership verification, and one-time-token ownership transfer, and its owner-actions list SHALL mark the actions that are available only for ESPN leagues (Refresh League, Turn Off Auto-Refresh, Invite Leaguemates) as ESPN only.

#### Scenario: Ownership instructions
- **WHEN** the Ownership & Access section renders
- **THEN** it documents the first-connector-is-owner model, that owner-only actions are hidden from non-owners, how a non-owner joins a private ESPN league via membership verification (with the "Join league" dialog screenshot), and the one-time-token ownership transfer/claim flow

#### Scenario: ESPN-only owner actions labeled
- **WHEN** the owner-actions list renders
- **THEN** the Refresh League, Turn Off Auto-Refresh, and Invite Leaguemates entries are labeled as ESPN only
