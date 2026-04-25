import { apiClient } from '@/lib/api-client';

export interface BracketMatch {
  match_id: number;
  round: number;
  team_1_id: string;
  team_1_display_name: string;
  team_1_team_name: string;
  team_1_team_logo: string | null;
  team_2_id: string;
  team_2_display_name: string;
  team_2_team_name: string;
  team_2_team_logo: string | null;
  winner: string | null;
  loser: string | null;
  position: number | null;
  team_1_from: string | null;
  team_2_from: string | null;
  season: string;
  team_1_score?: number;
  team_2_score?: number;
}

export interface Matchup {
  team_a_id: string;
  team_a_display_name: string;
  team_a_team_name: string;
  team_a_team_logo: string | null;
  team_a_score: number;
  team_a_starters: any[];
  team_a_bench: any[];
  team_b_id: string;
  team_b_display_name: string;
  team_b_team_name: string;
  team_b_team_logo: string | null;
  team_b_score: number;
  team_b_starters: any[];
  team_b_bench: any[];
  week: string;
  season: string;
  playoff_tier_type: string;
  playoff_round: string | null;
  winner: string;
  loser: string;
}

export interface GetPlayoffBracketResponse {
  data: BracketMatch[];
}

export interface GetMatchupsResponse {
  data: Matchup[];
}

export function getPlayoffBracket(
  leagueId: string,
  platform: 'ESPN' | 'SLEEPER',
  season: string,
): Promise<GetPlayoffBracketResponse> {
  const params = new URLSearchParams({
    platform,
    queryType: `PLAYOFF_BRACKET#${season}`,
  });
  return apiClient.get<GetPlayoffBracketResponse>(
    `/leagues/${leagueId}/query?${params}`,
  );
}

export function getMatchups(
  leagueId: string,
  platform: 'ESPN' | 'SLEEPER',
  season: string,
): Promise<GetMatchupsResponse> {
  const params = new URLSearchParams({
    platform,
    queryType: `MATCHUPS#${season}#`,
  });
  return apiClient.get<GetMatchupsResponse>(
    `/leagues/${leagueId}/query?${params}`,
  );
}
