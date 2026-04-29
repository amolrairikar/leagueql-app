import { apiClient } from '@/lib/api-client';
import type { Platform, MatchupItem } from '@/components/api/types';

export type { MatchupItem };

export function getAllSeasonsMatchups(
  leagueId: string,
  platform: Platform,
): Promise<MatchupItem[]> {
  const params = new URLSearchParams({ platform, queryType: 'MATCHUPS#' });
  return apiClient
    .get<{ data: MatchupItem[] }>(`/leagues/${leagueId}/query?${params}`)
    .then((res) => res.data);
}
