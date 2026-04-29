import { apiClient } from '@/lib/api-client';
import type { Platform, MatchupItem, GetLeagueResponse } from './types';

export function getLeague(
  leagueId: string,
  platform: Platform,
): Promise<GetLeagueResponse> {
  const params = new URLSearchParams({ platform });
  return apiClient.get<GetLeagueResponse>(`/leagues/${leagueId}?${params}`);
}

export function getAllMatchups(
  leagueId: string,
  platform: Platform,
): Promise<{ data: MatchupItem[] }> {
  const params = new URLSearchParams({ platform, queryType: 'MATCHUPS#' });
  return apiClient.get(`/leagues/${leagueId}/query?${params}`);
}
