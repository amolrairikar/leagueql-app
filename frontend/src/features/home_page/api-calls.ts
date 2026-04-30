import { apiClient } from '@/lib/api-client';
import type { Platform, SeasonStandingsItem, MatchupItem } from '@/components/api/types';

export function getAllSeasonStandings(
  leagueId: string,
  platform: Platform,
): Promise<{ data: SeasonStandingsItem[] }> {
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
  const params = new URLSearchParams({
    platform,
    queryType: 'MATCHUPS#',
  });
  return apiClient.get(`/leagues/${leagueId}/query?${params}`);
}
