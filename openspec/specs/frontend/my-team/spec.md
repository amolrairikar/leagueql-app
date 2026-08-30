# my-team Specification

## Purpose
A personal "how is my team doing?" report card at `/my_team`. The user picks one team in the
league; the page then presents that team's season at a glance — an overall grade and written
verdict, headline KPIs, recent form, where it stacks up, its draft and trade reports, and a ranked
list of insights. Everything is computed entirely client-side from the `SEASON_STANDINGS`,
`WEEKLY_STANDINGS`, `MATCHUPS`, `DRAFT`, and `TRANSACTIONS` views; all prose is assembled
deterministically from those computed facts (no LLM).

## Requirements

### Requirement: Select and persist the viewed team
Because the app has no viewer→team mapping, `/my_team` SHALL let the user pick which team to view
from the league roster and SHALL persist that choice per league so it survives reload, defaulting
to the first team when no valid choice is stored.

#### Scenario: Pick a team
- **WHEN** the user opens `/my_team` and chooses a team from the header selector
- **THEN** every section re-computes and re-renders for that team, identified by its `owner_id`
  resolved to the selected season's `team_id`

#### Scenario: Persisted default
- **WHEN** the user returns to `/my_team` in the same league
- **THEN** the previously chosen team is preselected; if none is stored or the stored team is not in
  the selected season, the first team (alphabetical by manager) is selected

### Requirement: Show an overall grade and written verdict
The hero SHALL show the team's identity, an overall letter grade, and a one-line verdict, where the
grade is a deterministic league-relative blend of all-play win %, points-for percentile, actual
win %, and lineup efficiency, and the verdict is templated from the team's top insight.

#### Scenario: Grade reflects true strength over record
- **WHEN** a team scores among the league's best but has an unlucky record (low seed)
- **THEN** its grade reflects the strength-weighted composite (grading above its seed), not its
  win-loss record alone

#### Scenario: Verdict is deterministic
- **WHEN** the hero renders for a team
- **THEN** the verdict sentence is generated from that team's highest-ranked insight using a fixed
  template filled with the team's computed numbers

### Requirement: Show headline KPIs and power ranking
The page SHALL show a KPI row for the selected team — record, standing, power ranking with
week-over-week movement, points-for with league rank, all-play record, and luck (actual vs expected
wins) — computed client-side.

#### Scenario: KPIs
- **WHEN** the page renders for a team
- **THEN** it shows record, standing, power rank (with up/down/flat movement vs the prior week),
  points-for and its league rank, all-play record, and luck as actual-minus-expected wins

### Requirement: Show recent form and comparative meters
The page SHALL show the team's recent results (most recent first, with opponent and score) and
meters comparing the team to the league on points-for, lineup efficiency, strength of schedule, and
expected vs actual wins.

#### Scenario: Recent form
- **WHEN** the team has played games in the selected season
- **THEN** its most recent results render newest-first with each result (win/loss), opponent, and
  final score, linking out to the matchups page

#### Scenario: Comparative meters
- **WHEN** the "how you stack up" section renders
- **THEN** it shows the team's points-for percentile, lineup efficiency, strength of schedule, and
  expected-vs-actual wins relative to the league

### Requirement: Show draft report
The page SHALL show the team's best and worst draft picks for the season, each with the player, the
draft slot, and the rank delta, computed from the `DRAFT` view with the shared draft-grading logic.

#### Scenario: Best and worst pick
- **WHEN** the selected team has scorable draft picks
- **THEN** the report shows the highest-delta pick as the best (a steal when the delta clears the
  steal threshold) and the lowest-delta pick as the worst (a bust when it clears the bust
  threshold), each with its round/pick and rank delta

#### Scenario: No draft data
- **WHEN** the season has no draft data for the team
- **THEN** the draft report shows an empty state rather than crashing

### Requirement: Show trade report gated to Sleeper
The page SHALL show the team's best and worst trades by rest-of-season point value on Sleeper
leagues, and SHALL show a graceful unavailable state (no error) on ESPN leagues, which expose no
transactions.

#### Scenario: Trades on Sleeper
- **WHEN** the league is on Sleeper and the team has completed trades
- **THEN** the report shows the trade with the best net rest-of-season point value and the one with
  the worst, each with what was acquired and the net points

#### Scenario: ESPN or no trades
- **WHEN** the league is on ESPN, or the team has no trades
- **THEN** the trade report shows an "available on Sleeper" / no-trades state without an error and
  trade-based insights do not appear

### Requirement: Show a ranked insights list from a rule catalog
The page SHALL render a list of insights produced by evaluating a catalog of insight rules against
the team's computed metrics, keeping the rules that apply, ranking them by severity, and rendering
the top ones with a sentiment, a templated sentence, and a backing metric.

#### Scenario: Insights fire and rank
- **WHEN** the insights section renders for a team
- **THEN** only insight rules whose conditions are met appear, ordered by severity, each showing its
  sentiment (good/watch/bad), a sentence templated from the team's numbers, and the metric behind it

#### Scenario: Data-guarded insights
- **WHEN** the data a rule needs is unavailable (e.g. trades on ESPN, or no bench data)
- **THEN** that rule does not fire and no partially-filled insight is shown

### Requirement: Handle load failures and empty data
A failed view load SHALL surface an inline message and an empty/insufficient season SHALL surface an
empty state, never crashing the page.

#### Scenario: Load failure
- **WHEN** a required view fails to load
- **THEN** the affected section shows an inline error message rather than blank or broken content

#### Scenario: Empty season
- **WHEN** the selected season has no matchup/standings data yet
- **THEN** the page shows an empty state rather than rendering partial or broken sections
