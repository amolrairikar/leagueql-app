# Design

## Context

See proposal.md (Why). The current state that shapes the approach:

- **Round labels** are two hardcoded `CASE` blocks in `src/processor/queries.py`: one in
  `MATCHUPS.ESPN` (Yahoo reuses it) and one in `MATCHUPS.SLEEPER`. Both map fixed week numbers to
  Quarterfinals/Semifinals/Finals based on whether the season is before or after 2021.
- **Week units differ by platform.** ESPN `week` is the matchup period (`matchupPeriodId`), so a
  two-week round is one period. Yahoo and Sleeper `week` is the NFL week.
  `build_league_settings_row` already stores `playoff_week_start` in each platform's own units
  (ESPN: `matchupPeriodCount + 1`). Values from it can be compared directly with `week`.
- **Defaults are hidden.** `build_league_settings_row` silently fills in week 15 (or 14) and 6
  teams. Only `num_playoff_teams_assumed` records that a default was used; the start week has no
  such flag.
- **The ESPN/Yahoo bracket** (`_build_espn_brackets`) numbers rounds by the distinct playoff weeks
  it has seen so far and gives placements to the highest round seen.
- **Sleeper brackets** carry an explicit round (`r`) for every match, including later rounds that
  haven't been seeded yet. Sleeper playoff matchups are tiered by looking up each team pair in
  the bracket.
- **Champion:** the `STANDINGS` champion CTE picks the lone winners-bracket game in the last
  winners-bracket week.
- **Manager Comparison** loads only matchups (`getAllSeasonsMatchups`). Manager History already
  loads STANDINGS for every season.

## Goals / Non-Goals

**Goals:**
- Compute "which round is this week" in one place in Python and use it for labels, bracket rounds
  and placements. The champion then follows from the "Finals" label.
- Keep the shapes of every stored view the same.

**Non-Goals:**
- Sleeper multi-week rounds (Sleeper's `playoff_round_type`). Each NFL week of a two-week Sleeper
  round gets the same label from the bracket, but deciding the winner of a two-week Sleeper
  final across both weeks is out of scope; the champion behaves as it does today for those
  leagues.
- The playoff-bracket page's score-to-week join (`championshipWeekFor`). It stays valid: the
  rounds present are always 1..k, and round k is in the latest playoff week.
- Persisting a new `LEAGUE_SETTINGS` field.

## Decisions

### D1. Compute the structure in Python and attach `round_num` / `total_rounds` to each matchup row
Each platform's `_register_*_raw_data` already builds `all_matchups` in Python and has that
season's settings at hand. Add a helper, `playoff_structure(settings_row) -> (first_week,
total_rounds) | None`. It returns `None` when either value was defaulted. Then set two fields on
every winners-bracket matchup row: `playoff_round_num` and `playoff_total_rounds`.
- **ESPN/Yahoo:** `round_num = week - first_week + 1`.
- **Sleeper:** `round_num = bracket_entry["r"]` and `total_rounds = max(r)` over the winners
  bracket. Sleeper's own rounds already account for multi-week rounds.
- **Fallback (no structure):** compute from the season's observed winners-bracket weeks, as
  described in the spec requirement "Fall back to observed playoff weeks when settings are
  defaulted". A completed season (last week has exactly one game) gets
  `total_rounds = number of observed weeks`. An in-progress season gets
  `total_rounds = NULL`, which produces "Round N" labels.

The SQL `CASE` blocks then become one platform-agnostic mapping from
`total_rounds - round_num` (0 → Finals, 1 → Semifinals, 2 → Quarterfinals, otherwise or when
`total_rounds` is NULL → `'Round ' || round_num`).

*Alternative considered:* doing everything in SQL by joining a `league_settings` view in DuckDB.
Rejected because Sleeper's round has to come from the bracket lookup, which only happens in
Python, and computing the structure in two languages invites the two to drift apart.

### D2. Track defaulted settings without persisting them
Add `playoff_week_start_assumed` to the dict `build_league_settings_row` returns, as the
counterpart of `num_playoff_teams_assumed`. `playoff_structure` requires both flags to be false.
Strip the new key before the `LEAGUE_SETTINGS` item is written so the item's schema doesn't
change.

*Alternative:* persist it. Rejected because no consumer needs it yet; it can be added later
without changing this design.

### D3. `ceil(log2(num_playoff_teams))` rounds
A 6-team playoff gives 3 rounds, with byes in round 1. That matches how ESPN, Yahoo and Sleeper
build brackets for 3–16 teams. A count below 2 makes `playoff_structure` return `None`, so the
fallback applies.

### D4. The bracket builder reuses the same round numbers
`_build_espn_brackets` takes `round` from `playoff_round_num` (D1) instead of its `week_to_round`
enumeration. It assigns placements only where `round == playoff_total_rounds`. When
`total_rounds` is NULL (in-progress fallback), it assigns no placements, so a partly-played
bracket never has a `position = 1` match. Feeder links (`team_*_from`) still look up
`round - 1`. Settings-derived rounds always run 1..k without gaps, because every winners-bracket
round has at least one game.

### D5. The champion is the decided "Finals" winner
Replace the `winners_bracket_weeks` CTE with
`WHERE playoff_tier_type = 'WINNERS_BRACKET' AND playoff_round = 'Finals' AND winner <> 'TIE'`.
A 0–0 placeholder final has winner `TIE` and so names no champion. Sleeper two-week finals
(see Non-Goals) could produce two "Finals" rows; to keep today's behavior there, take the row
with the latest week (`QUALIFY ROW_NUMBER() OVER (PARTITION BY season ORDER BY week DESC) = 1`).

### D6. Manager Comparison reads STANDINGS
`getAllSeasonsMatchups` becomes `getComparisonData`, which also issues the same single
`SEASON_STANDINGS#` prefix query Manager History uses, in parallel with matchups.
Championships are counted from rows with `champion === 'Yes'`, keyed by the
migration-mapped `owner_id`, and the `'Finals'` scan is removed. A no-data `404` for
standings counts as no rows. Any other standings failure rejects like a matchups failure
does today and is handled by the app error boundary; the feature has no inline error state.

*Alternative:* keep deriving titles from matchups now that the labels are right. Rejected because
it keeps two definitions of "champion", and an in-progress fallback season could still mislabel a
round.

## Risks / Trade-offs

- **[Risk] A commissioner changes the playoff settings mid-season.** The stored structure is
  whatever the latest refresh read, so labels can change between refreshes. → Acceptable: every
  refresh recomputes the latest season, and completed seasons' settings are final.
- **[Risk] A platform's real start week disagrees with its observed bracket** (e.g. a league
  that changed the playoff start after games were played). → Winners-bracket games whose
  `round_num` falls outside `1..total_rounds` fall back to the observed-weeks rule for that
  season, and a warning is logged.
- **[Trade-off] "Round N" is a new `playoff_round` value.** It only appears for in-progress
  seasons with defaulted settings. The Matchups page shows any string as a badge, and its sort
  puts unknown labels with the winners-bracket labels. → Document it in
  `docs/db/dynamodb_spec.md`.
- **[Risk] Stored views stay wrong until reprocessed.** → See Migration Plan.

## Migration Plan

1. Deploy the processor first. It is backward compatible: field shapes are unchanged and labels
   are only more correct.
2. Deploy the frontend (Manager Comparison standings fetch). It works against old data too:
   champions on old data are already correct for complete seasons in the common case.
3. Existing leagues pick up correct labels for the latest season on their next refresh. Past
   seasons need `reprocess_all` (or `reprocess_seasons`) through the existing admin/backfill
   path. No new migration script is needed.
4. Rollback: revert the processor. The views keep their schema, and the next reprocess restores
   the old labels.
