import { apiClient } from '@/lib/api-client';
import { isDemoMode } from '@/lib/cookie-handler';
import { queryDemoLeague } from '@/lib/demo-api';
import type { Platform, SeasonStandingsItem, MatchupItem } from '@/components/api/types';

export function getAllSeasonStandings(
  leagueId: string,
  platform: Platform,
): Promise<{ data: SeasonStandingsItem[] }> {
  if (isDemoMode()) return queryDemoLeague<SeasonStandingsItem>('SEASON_STANDINGS#');
  const params = new URLSearchParams({
    platform,
    queryType: 'SEASON_STANDINGS#',
  });
  return apiClient.get(`/leagues/${leagueId}/query?${params}`);
}

export function getAllSeasonMatchups(
  leagueId: string,
  platform: Platform,
): Promise<{ data: MatchupItem[] }> {
  if (isDemoMode()) return queryDemoLeague<MatchupItem>('MATCHUPS#');
  const params = new URLSearchParams({
    platform,
    queryType: 'MATCHUPS#',
  });
  return apiClient.get(`/leagues/${leagueId}/query?${params}`);
}
