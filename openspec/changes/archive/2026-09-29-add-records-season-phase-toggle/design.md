# Design

## Context

Both records pages fetch every matchup via `getAllMatchups` and compute their boards client-side.
Each `MatchupItem` already carries `playoff_tier_type`: `NONE` for regular-season games, and a
bracket tier (`WINNERS_BRACKET`, losers, consolation) for postseason games.

## Decisions

- **Two states, default Regular season.** The complaint is that multi-week playoff games distort
  the boards, so the default view removes them. There is no "All games" option: mixing phases is
  exactly what skews the results.
- **Postseason = any non-`NONE` tier**, matching manager history's "Postseason" divider. A missing
  tier counts as regular season, matching the schedule-swap simulator.
- **Shared helper and control.** `isRegularSeasonMatchup` lives next to `isUnplayedMatchup` in
  `lib/matchups.ts`. A small `SeasonPhaseToggle` component renders the same label/Switch/label
  layout as the home page's all-time standings toggle and is used by both records pages.
- **Filter before extraction.** Matchups are filtered to the selected phase before records are
  extracted; the Season/Manager filters then apply as before. The Season (and Manager) dropdown
  options are derived from both phases, so switching phase never empties them.
  An empty phase falls through to the existing "No records match the selected filters." message.
