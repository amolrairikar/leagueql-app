import { getSeasonMatchups, queryLeague } from '@/components/api/leagues';
import type { Platform } from '@/components/api/types';

export type { PlayerStat, MatchupItem } from '@/components/api/types';
export { getSeasonMatchups };

export interface WeeklyStandingItem {
  season: string;
  snapshot_week: string;
  team_id: string;
  owner_id: string;
  owner_username: string;
  games_played: number;
  wins: number;
  losses: number;
  ties: number;
  record: string;
}

export function getSeasonWeeklyStandings(
  leagueId: string,
  platform: Platform,
  season: string,
): Promise<{ data: WeeklyStandingItem[] }> {
  return queryLeague<WeeklyStandingItem>(
    leagueId,
    platform,
    `WEEKLY_STANDINGS#${season}`,
  );
}
