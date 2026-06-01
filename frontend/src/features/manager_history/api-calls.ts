import { queryLeague, getMigrationMapping } from '@/components/api/leagues';
import type { Platform, MatchupItem } from '@/components/api/types';

export type { MatchupItem };
export type { PlatformMigrationEntry } from '@/components/api/leagues';

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
  migrationMapping: Map<string, string>;
}> {
  const [standingsResult, matchupResult, migrationMapping] = await Promise.all([
    queryLeague<ManagerStandingsItem>(
      leagueId,
      platform,
      'SEASON_STANDINGS#',
    ).then((r) => r.data),
    queryLeague<MatchupItem>(leagueId, platform, 'MATCHUPS#').then(
      (r) => r.data,
    ),
    getMigrationMapping(leagueId, platform),
  ]);

  const standings = standingsResult.filter((s) => seasons.includes(s.season));
  const matchups = matchupResult.filter((m) => seasons.includes(m.season));

  return { standings, matchups, migrationMapping };
}
