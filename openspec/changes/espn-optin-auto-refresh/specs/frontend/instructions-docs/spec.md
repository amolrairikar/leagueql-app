## MODIFIED Requirements

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
