import { apiClient } from '@/lib/api-client';

export interface TeamItem {
  team_id: string;
  team_name: string;
  team_logo: string | null;
  display_name: string;
  season: string;
  primary_owner_id: string | null;
  secondary_owner_id: string | null;
}

export interface MatchupItem {
  team_a_id: string;
  team_a_score: number;
  team_b_id: string;
  team_b_score: number;
  playoff_tier_type: string;
  playoff_round: string | null;
  winner: string;
  loser: string;
  week: string;
  season: string;
  team_a_primary_owner_id: string;
  team_b_primary_owner_id: string;
}

export function getTeams(
  leagueId: string,
  platform: 'ESPN' | 'SLEEPER',
  season: string,
): Promise<{ data: TeamItem[] }> {
  const params = new URLSearchParams({
    platform,
    queryType: `TEAMS#${season}`,
  });
  return apiClient.get(`/leagues/${leagueId}/query?${params}`);
}

export function getSeasonMatchups(
  leagueId: string,
  platform: 'ESPN' | 'SLEEPER',
  season: string,
): Promise<{ data: MatchupItem[] }> {
  const params = new URLSearchParams({
    platform,
    queryType: `MATCHUPS#${season}#`,
  });
  return apiClient.get(`/leagues/${leagueId}/query?${params}`);
}
