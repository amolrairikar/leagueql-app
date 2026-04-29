import { apiClient } from '@/lib/api-client';
import type { Platform, SeasonStandingsItem, MatchupItem } from '@/components/api/types';

export type { GetLeagueResponse } from '@/components/api/types';
export { getLeague } from '@/components/api/leagues';

export function getAllSeasonStandings(
  leagueId: string,
  platform: Platform,
): Promise<{ data: SeasonStandingsItem[] }> {
  const params = new URLSearchParams({
    platform,
    queryType: 'SEASON_STANDINGS#',
  });
  console.log('[getAllSeasonStandings] Calling API with:', `/leagues/${leagueId}/query?${params}`);
  return apiClient.get(`/leagues/${leagueId}/query?${params}`);
}

export function getAllSeasonMatchups(
  leagueId: string,
  platform: Platform,
): Promise<{ data: MatchupItem[] }> {
  const params = new URLSearchParams({
    platform,
    queryType: 'MATCHUPS#',
  });
  console.log('[getAllSeasonMatchups] Calling API with:', `/leagues/${leagueId}/query?${params}`);
  return apiClient.get(`/leagues/${leagueId}/query?${params}`);
}
