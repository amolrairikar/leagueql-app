import type { MatchupItem } from '@/components/api/types';

/**
 * An in-progress season persists its future/unplayed weeks as `0-0` placeholder
 * matchups. A genuinely played fantasy game essentially never ends with both teams
 * on exactly `0` (scores are fractional), so both scores being exactly `0` is a
 * reliable proxy for "unplayed". This mirrors the backend STANDINGS/WEEKLY_STANDINGS
 * exclusion so client-side aggregations never count placeholder weeks. A real game
 * where one team scores `0` is retained because the other side is `> 0`.
 */
export function isUnplayedMatchup(m: MatchupItem): boolean {
  return m.team_a_score === 0 && m.team_b_score === 0;
}
