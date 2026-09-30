# Design

## Context

Yahoo's scoreboard marks each game only as "playoff" and "consolation", where consolation means
the bracket for teams that missed the playoffs. Placement games between playoff teams (3rd place,
5th place) come back as non-consolation playoff games, so they can't be told apart from
championship-path games by their flags. In the reported league (6 teams, playoffs weeks 15–17),
the week-17 3rd-place game and the final were both tagged `WINNERS_BRACKET`. The STANDINGS
`champion` CTE then marked both winners as champions.

## Decisions

- **Tier by elimination, per season, in week order.** Track the teams that have lost a
  non-consolation playoff game. A non-consolation playoff game where neither team is eliminated
  is `WINNERS_BRACKET`, and its loser is eliminated once the week is done. Any other
  non-consolation playoff game is `WINNERS_CONSOLATION_LADDER`, and Yahoo consolation games are
  `LOSERS_CONSOLATION_LADDER`. These match ESPN's tier values, so the reused ESPN MATCHUPS and
  PLAYOFF_BRACKET transforms and `_build_espn_brackets` work as they are. `_build_espn_brackets`
  already drops the losers tier and marks the final-round consolation game as position 3.
- **Champion = winner of the last winners-bracket week.** This replaces the hard-coded
  week-16/17 rule. Once tiers are correct it matches ESPN and Sleeper, and it also handles
  Yahoo leagues whose playoffs end before week 17.
- **Week from the week calendar.** A Yahoo transaction has no week, so onboarding fetches the
  game's week calendar (start and end date per week) for each season. A transaction belongs to
  the first week whose end date is on or after the transaction's date, in US Eastern time with a
  fixed UTC−5 offset (so no tz database is needed in Lambda). Moves before week 1 clamp to week 1
  and moves after the last week clamp to the last week. If the calendar is missing, `week`
  stays null (the old behavior).
- **Created in ms.** `created = int(timestamp) * 1000`, which matches the ESPN and Sleeper
  `created` units that the frontend passes to `new Date()`.

## Risks

- Old raw payloads don't include the week calendar. Their transaction weeks stay null until the
  league is refreshed.
