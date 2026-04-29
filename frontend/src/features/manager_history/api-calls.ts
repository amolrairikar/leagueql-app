import { apiClient } from '@/lib/api-client';
import type { Platform, MatchupItem } from '@/components/api/types';

export type { MatchupItem };

export interface ManagerStandingsItem {
  season: string;
  team_id: string;
  owner_id: string;
  team_name: string;
  team_logo: string | null;
  owner_username: string;
  final_rank: number | null;
  games_played: number;
  wins: number;
  losses: number;
  ties: number;
  record: string;
  total_pf: number;
  avg_pf: number;
  champion: string;
}

export async function getManagerHistoryData(
  leagueId: string,
  platform: Platform,
  seasons: string[],
): Promise<{
  standings: ManagerStandingsItem[];
  matchups: MatchupItem[];
}> {
  console.log('[getManagerHistoryData] Fetching all standings and matchups in single queries');
  const [standingsResult, matchupResult] = await Promise.all([
    apiClient
      .get<{
        data: ManagerStandingsItem[];
      }>(
        `/leagues/${leagueId}/query?${new URLSearchParams({ platform, queryType: 'SEASON_STANDINGS#' })}`,
      )
      .then((r) => r.data),
    apiClient
      .get<{
        data: MatchupItem[];
      }>(
        `/leagues/${leagueId}/query?${new URLSearchParams({ platform, queryType: 'MATCHUPS#' })}`,
      )
      .then((r) => r.data),
  ]);

  const standings = standingsResult.filter((s) => seasons.includes(s.season));
  const matchups = matchupResult.filter((m) => seasons.includes(m.season));

  return { standings, matchups };
}
