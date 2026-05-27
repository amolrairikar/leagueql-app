import { apiClient } from '@/lib/api-client';
import { isDemoMode } from '@/lib/cookie-handler';
import { queryDemoLeague } from '@/lib/demo-api';
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
  if (isDemoMode()) return queryDemoLeague<WeeklyStandingItem>(`WEEKLY_STANDINGS#${season}`);
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
  if (isDemoMode()) return queryDemoLeague<MatchupItem>(`MATCHUPS#${season}#`);
  const params = new URLSearchParams({
    platform,
    queryType: `MATCHUPS#${season}#`,
  });
  return apiClient.get(`/leagues/${leagueId}/query?${params}`);
}
