import type { BracketMatch, Matchup } from './api-calls';

import type { Team } from '@/features/playoff_bracket/team';

export interface WildcardRoundItem {
  byeTeam: Team | null;
  wildcardMatch: BracketMatch | null | undefined;
}

/** Pair each semifinal's bye team with the wildcard matchup feeding its other slot. */
export function buildWildcardRoundItems(
  semifinals: BracketMatch[],
  wildcard: BracketMatch[],
): WildcardRoundItem[] {
  return semifinals.map((semi) => {
    // Determine which team had a bye and which comes from a wildcard match
    let byeTeamId: string | null = null;
    let wildcardMatchId: number | null = null;

    if (semi.team_1_from === null) {
      byeTeamId = semi.team_1_id;
      // team_2_from should be like {"w": 1} or {"l": 1}
      if (semi.team_2_from) {
        const from = JSON.parse(semi.team_2_from) as { w?: number; l?: number };
        wildcardMatchId = from.w ?? from.l ?? null;
      }
    } else if (semi.team_2_from === null) {
      byeTeamId = semi.team_2_id;
      // team_1_from should be like {"w": 1} or {"l": 1}
      if (semi.team_1_from) {
        const from = JSON.parse(semi.team_1_from) as { w?: number; l?: number };
        wildcardMatchId = from.w ?? from.l ?? null;
      }
    }

    const wildcardMatch = wildcardMatchId
      ? wildcard.find((m) => m.match_id === wildcardMatchId)
      : null;
    const byeTeam = byeTeamId
      ? {
          team_id: byeTeamId,
          display_name:
            semi.team_1_id === byeTeamId
              ? semi.team_1_display_name
              : semi.team_2_display_name,
          team_name:
            semi.team_1_id === byeTeamId
              ? semi.team_1_team_name
              : semi.team_2_team_name,
          team_logo:
            semi.team_1_id === byeTeamId
              ? semi.team_1_team_logo
              : semi.team_2_team_logo,
        }
      : null;

    return { byeTeam, wildcardMatch };
  });
}

/** Find the weekly matchup (with lineups) behind a bracket match, if one was played. */
export function findMatchupForBracketMatch(
  matchups: Matchup[],
  championshipWeek: number,
  maxRound: number,
  bracketMatch: BracketMatch,
): Matchup | null {
  const week = championshipWeek - (maxRound - bracketMatch.round);
  return (
    matchups.find(
      (m) =>
        m.season === bracketMatch.season &&
        parseInt(m.week, 10) === week &&
        ((m.team_a_id === bracketMatch.team_1_id &&
          m.team_b_id === bracketMatch.team_2_id) ||
          (m.team_a_id === bracketMatch.team_2_id &&
            m.team_b_id === bracketMatch.team_1_id)),
    ) ?? null
  );
}
