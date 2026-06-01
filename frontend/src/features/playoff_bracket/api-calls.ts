import { queryLeague } from '@/components/api/leagues';
import type { Platform, MatchupItem } from '@/components/api/types';

export type Matchup = MatchupItem;

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

export interface GetPlayoffBracketResponse {
  data: BracketMatch[];
}

export interface GetMatchupsResponse {
  data: MatchupItem[];
}

export interface WeeklyStandingItem {
  season: string;
  snapshot_week: string;
  team_id: string;
  record: string;
}

export interface GetWeeklyStandingsResponse {
  data: WeeklyStandingItem[];
}

export function getPlayoffBracket(
  leagueId: string,
  platform: Platform,
  season: string,
): Promise<GetPlayoffBracketResponse> {
  return queryLeague<BracketMatch>(
    leagueId,
    platform,
    `PLAYOFF_BRACKET#${season}`,
  );
}

export function getMatchups(
  leagueId: string,
  platform: Platform,
  season: string,
): Promise<GetMatchupsResponse> {
  return queryLeague<MatchupItem>(leagueId, platform, `MATCHUPS#${season}#`);
}

export function getWeeklyStandings(
  leagueId: string,
  platform: Platform,
  season: string,
): Promise<GetWeeklyStandingsResponse> {
  return queryLeague<WeeklyStandingItem>(
    leagueId,
    platform,
    `WEEKLY_STANDINGS#${season}`,
  );
}
