import { queryLeague } from '@/components/api/leagues';
import type { MatchupItem, Platform } from '@/components/api/types';

export type { MatchupItem } from '@/components/api/types';

/** Regular-season + playoff matchups for one season (weekly awards, frontend/weekly-awards). */
export function getSeasonMatchups(
  leagueId: string,
  platform: Platform,
  season: string,
): Promise<{ data: MatchupItem[] }> {
  return queryLeague<MatchupItem>(leagueId, platform, `MATCHUPS#${season}#`);
}
