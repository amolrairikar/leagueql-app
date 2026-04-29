import { apiClient } from '@/lib/api-client';
import type { Platform, MatchupItem } from '@/components/api/types';

export type { PlayerStat, MatchupItem } from '@/components/api/types';

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
  const params = new URLSearchParams({
    platform,
    queryType: `WEEKLY_STANDINGS#${season}`,
  });
  return apiClient.get(`/leagues/${leagueId}/query?${params}`);
}

export function getSeasonMatchups(
  leagueId: string,
  platform: Platform,
  season: string,
): Promise<{ data: MatchupItem[] }> {
  const params = new URLSearchParams({
    platform,
    queryType: `MATCHUPS#${season}#`,
  });
  return apiClient.get(`/leagues/${leagueId}/query?${params}`);
}
