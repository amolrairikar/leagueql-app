import { apiClient } from '@/lib/api-client';
import { isDemoMode } from '@/lib/cookie-handler';
import { queryDemoLeague } from '@/lib/demo-api';
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
  if (isDemoMode())
    return queryDemoLeague<SeasonStandingsItem>(`SEASON_STANDINGS#${season}`);
  const params = new URLSearchParams({
    platform,
    queryType: `SEASON_STANDINGS#${season}`,
  });
  return apiClient.get<GetSeasonStandingsResponse>(
    `/leagues/${leagueId}/query?${params}`,
  );
}
