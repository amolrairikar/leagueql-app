import { queryLeague } from '@/components/api/leagues';
import type { Platform, SeasonStandingsItem } from '@/components/api/types';

export type { SeasonStandingsItem } from '@/components/api/types';

export interface GetSeasonStandingsResponse {
  data: SeasonStandingsItem[];
}

export function getSeasonStandings(
  leagueId: string,
  platform: Platform,
  season: string,
): Promise<GetSeasonStandingsResponse> {
  return queryLeague<SeasonStandingsItem>(
    leagueId,
    platform,
    `SEASON_STANDINGS#${season}`,
  );
}
