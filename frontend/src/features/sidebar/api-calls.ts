import { apiClient } from '@/lib/api-client';
import type { Platform } from '@/lib/cookie-handler';

export interface DeleteLeagueResponse {
  detail: string;
}

export function deleteLeague(
  leagueId: string,
  platform: Platform,
): Promise<DeleteLeagueResponse> {
  const params = new URLSearchParams({ platform });
  return apiClient.delete<DeleteLeagueResponse>(
    `/leagues/${leagueId}?${params}`,
  );
}
