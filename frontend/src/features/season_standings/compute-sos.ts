import type { MatchupItem, SeasonStandingsItem } from '@/components/api/types';
import { isRegularSeason } from '@/features/schedule_swap/compute-schedule-swap';
import { isUnplayedMatchup } from '@/lib/matchups';

/**
 * Strength of schedule per team (frontend/season-standings): the average season win% of every
 * opponent a team faced in the regular season — higher means a tougher
 * schedule. Computed client-side from the standings (for each team's win%) and
 * the season's matchups (for who faced whom); playoff games are excluded to
 * match how the standings win% itself is computed.
 *
 * Returns a `team_id -> SoS` map. A team is `null` when it has no regular-season
 * opponents, or when none of its opponents appear in the standings.
 */
export function computeStrengthOfSchedule(
  standings: SeasonStandingsItem[],
  matchups: MatchupItem[],
): Record<string, number | null> {
  const winPctById = new Map(standings.map((s) => [s.team_id, s.win_pct]));

  const opponentsById = new Map<string, string[]>();
  const addOpponent = (teamId: string, opponentId: string) => {
    const list = opponentsById.get(teamId);
    if (list) list.push(opponentId);
    else opponentsById.set(teamId, [opponentId]);
  };

  for (const m of matchups) {
    if (!isRegularSeason(m)) continue;
    // Unplayed 0-0 placeholder weeks add no real opponent to anyone's schedule.
    if (isUnplayedMatchup(m)) continue;
    addOpponent(m.team_a_id, m.team_b_id);
    addOpponent(m.team_b_id, m.team_a_id);
  }

  const sosById: Record<string, number | null> = {};
  for (const s of standings) {
    const opponentWinPcts = (opponentsById.get(s.team_id) ?? [])
      .map((id) => winPctById.get(id))
      .filter((p): p is number => p !== undefined);
    sosById[s.team_id] =
      opponentWinPcts.length > 0
        ? opponentWinPcts.reduce((a, b) => a + b, 0) / opponentWinPcts.length
        : null;
  }
  return sosById;
}
