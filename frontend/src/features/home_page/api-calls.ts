import { apiClient } from '@/lib/api-client';
import type { SeasonStandingsItem } from '@/features/season_standings/api-calls';
import type { MatchupItem } from '@/features/matchups/api-calls';

export interface LeagueResponse {
  detail: string;
  data: {
    canonical_league_id: string;
    seasons: string[];
    league_name?: string;
  };
}

export function getLeague(
  leagueId: string,
  platform: 'ESPN' | 'SLEEPER',
): Promise<LeagueResponse> {
  const params = new URLSearchParams({ platform });
  return apiClient.get<LeagueResponse>(`/leagues/${leagueId}?${params}`);
}

export function getAllSeasonStandings(
  leagueId: string,
  platform: 'ESPN' | 'SLEEPER',
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
  platform: 'ESPN' | 'SLEEPER',
): Promise<{ data: MatchupItem[] }> {
  const params = new URLSearchParams({
    platform,
    queryType: 'MATCHUPS#',
  });
  console.log('[getAllSeasonMatchups] Calling API with:', `/leagues/${leagueId}/query?${params}`);
  return apiClient.get(`/leagues/${leagueId}/query?${params}`);
}
