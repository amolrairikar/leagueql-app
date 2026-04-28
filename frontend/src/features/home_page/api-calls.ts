import { apiClient } from '@/lib/api-client';

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
