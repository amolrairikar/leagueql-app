import { queryLeague, getMigrationMapping } from '@/components/api/leagues';
import type { Platform, MatchupItem } from '@/components/api/types';
import { ApiError } from '@/lib/api-client';

export type { MatchupItem };

/** The STANDINGS fields the comparison reads: who won each season's title. */
export interface ChampionStandingsItem {
  season: string;
  owner_id: string;
  champion: string;
}

export interface ComparisonData {
  matchups: MatchupItem[];
  standings: ChampionStandingsItem[];
  migrationMapping: Map<string, string>;
}

export async function getComparisonData(
  leagueId: string,
  platform: Platform,
): Promise<ComparisonData> {
  const [matchups, standings, migrationMapping] = await Promise.all([
    queryLeague<MatchupItem>(leagueId, platform, 'MATCHUPS#').then(
      (res) => res.data,
    ),
    // Championships come from the STANDINGS champion flag (the processor's single
    // definition of a title). The backend 404s "no data" when no standings exist,
    // which is no champions, not a load error; other failures still reject.
    queryLeague<ChampionStandingsItem>(leagueId, platform, 'SEASON_STANDINGS#')
      .then((res) => res.data)
      .catch((err: unknown) => {
        if (err instanceof ApiError && err.status === 404) return [];
        throw err;
      }),
    getMigrationMapping(leagueId, platform),
  ]);
  return { matchups, standings, migrationMapping };
}
