import { apiClient } from '@/lib/api-client';

export interface SeasonStandingsItem {
  season: string;
  team_id: string;
  owner_id: string;
  games_played: number;
  wins: number;
  losses: number;
  ties: number;
  record: string;
  win_pct: number;
  total_vs_league_wins: number;
  total_vs_league_losses: number;
  win_pct_vs_league: number;
  total_pf: number;
  total_pa: number;
  avg_pf: number;
  avg_pa: number;
}

export interface GetSeasonStandingsResponse {
  data: SeasonStandingsItem[];
}

export function getSeasonStandings(
  leagueId: string,
  platform: 'ESPN' | 'SLEEPER',
  season: string,
): Promise<GetSeasonStandingsResponse> {
  const params = new URLSearchParams({
    platform,
    queryType: `SEASON_STANDINGS#${season}`,
  });
  return apiClient.get<GetSeasonStandingsResponse>(
    `/leagues/${leagueId}/query?${params}`,
  );
}
