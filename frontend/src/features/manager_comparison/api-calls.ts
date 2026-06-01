import { queryLeague, getMigrationMapping } from '@/components/api/leagues';
import type { Platform, MatchupItem } from '@/components/api/types';

export type { MatchupItem };

export async function getAllSeasonsMatchups(
  leagueId: string,
  platform: Platform,
): Promise<{ matchups: MatchupItem[]; migrationMapping: Map<string, string> }> {
  const [matchupsResult, migrationMapping] = await Promise.all([
    queryLeague<MatchupItem>(leagueId, platform, 'MATCHUPS#').then(
      (res) => res.data,
    ),
    getMigrationMapping(leagueId, platform),
  ]);
  return { matchups: matchupsResult, migrationMapping };
}
