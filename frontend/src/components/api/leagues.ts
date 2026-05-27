import { apiClient } from '@/lib/api-client';
import { isDemoMode } from '@/lib/cookie-handler';
import { getDemoLeague, queryDemoLeague } from '@/lib/demo-api';
import type { Platform, MatchupItem, GetLeagueResponse } from './types';

export function getLeague(
  leagueId: string,
  platform: Platform,
): Promise<GetLeagueResponse> {
  if (isDemoMode()) return getDemoLeague();
  const params = new URLSearchParams({ platform });
  return apiClient.get<GetLeagueResponse>(`/leagues/${leagueId}?${params}`);
}

export function getAllMatchups(
  leagueId: string,
  platform: Platform,
): Promise<{ data: MatchupItem[] }> {
  if (isDemoMode()) return queryDemoLeague<MatchupItem>('MATCHUPS#');
  const params = new URLSearchParams({ platform, queryType: 'MATCHUPS#' });
  return apiClient.get(`/leagues/${leagueId}/query?${params}`);
}
