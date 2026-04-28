import { apiClient } from '@/lib/api-client';
import { type MatchupItem } from '@/features/matchups/api-calls';

export type { MatchupItem };

export function getAllMatchups(
  leagueId: string,
  platform: 'ESPN' | 'SLEEPER',
): Promise<{ data: MatchupItem[] }> {
  const params = new URLSearchParams({ platform, queryType: 'MATCHUPS#' });
  return apiClient.get(`/leagues/${leagueId}/query?${params}`);
}
