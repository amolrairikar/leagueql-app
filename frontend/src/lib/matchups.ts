import type { MatchupItem } from '@/components/api/types';
import { assignAvatarColors } from '@/lib/color-constants';

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

/**
 * Deterministic team-id → avatar-color map for a set of matchups. Teams are
 * collected across both sides of every matchup and sorted by display name so a
 * team keeps the same color regardless of the order matchups arrive in. Shared
 * by the record-board features (matchup records, player records).
 */
export function buildTeamColorMap(
  matchups: MatchupItem[],
): Map<string, string> {
  const uniqueTeams = new Map<string, string>();
  for (const m of matchups) {
    uniqueTeams.set(m.team_a_id, m.team_a_display_name ?? '');
    uniqueTeams.set(m.team_b_id, m.team_b_display_name ?? '');
  }
  const sortedIds = [...uniqueTeams.entries()]
    .sort((a, b) => a[1].localeCompare(b[1]))
    .map(([id]) => id);
  return assignAvatarColors(sortedIds);
}
