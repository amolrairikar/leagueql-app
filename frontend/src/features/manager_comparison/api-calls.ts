import type { MatchupItem } from '@/features/matchups/api-calls';
import { apiClient } from '@/lib/api-client';

export type { MatchupItem };

export function getAllSeasonsMatchups(
  leagueId: string,
  platform: 'ESPN' | 'SLEEPER',
  seasons: string[],
): Promise<MatchupItem[]> {
  return Promise.all(
    seasons.map((season) => {
      const params = new URLSearchParams({
        platform,
        queryType: `MATCHUPS#${season}#`,
      });
      return apiClient
        .get<{ data: MatchupItem[] }>(`/leagues/${leagueId}/query?${params}`)
        .then((res) => res.data);
    }),
  ).then((results) => results.flat());
}
