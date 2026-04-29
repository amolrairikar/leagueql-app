export type Platform = 'ESPN' | 'SLEEPER';

export interface PlayerStat {
  player_id: number;
  full_name: string;
  points_scored: number;
  position: string;
  fantasy_position?: string;
}

export interface MatchupItem {
  team_a_id: string;
  team_a_display_name: string;
  team_a_team_name: string;
  team_a_team_logo: string | null;
  team_a_score: number;
  team_a_starters: PlayerStat[];
  team_a_bench: PlayerStat[];
  team_a_primary_owner_id: string;
  team_a_secondary_owner_id: string | null;
  team_b_id: string;
  team_b_display_name: string;
  team_b_team_name: string;
  team_b_team_logo: string | null;
  team_b_score: number;
  team_b_starters: PlayerStat[];
  team_b_bench: PlayerStat[];
  team_b_primary_owner_id: string;
  team_b_secondary_owner_id: string | null;
  playoff_tier_type: string;
  playoff_round: string | null;
  winner: string;
  loser: string;
  week: string;
  season: string;
}

export interface SeasonStandingsItem {
  season: string;
  team_id: string;
  owner_id: string;
  team_name: string;
  team_logo: string;
  owner_username: string;
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
  champion: string;
}

export interface GetLeagueResponse {
  detail: string;
  data: {
    canonical_league_id: string;
    seasons: string[];
    league_name?: string;
  };
}
