import type { Platform } from '@/components/api/types';
import { apiClient } from '@/lib/api-client';
import { isDemoMode } from '@/lib/cookie-handler';
import { getDemoMyTeam } from '@/lib/demo-api';

export { getManagerHistoryData } from '@/features/manager_history/api-calls';
export { getLeagueSettings } from '@/features/playoff_race_predictor/api-calls';

export interface MyTeamPrefs {
  /** Platform owner ID of the claimed team; null when the user has not claimed one. */
  owner_id: string | null;
}

export interface MyTeamResponse {
  detail: string;
  data: MyTeamPrefs;
}

/**
 * The caller's claimed team for a league (backend/user-league-preferences). In demo
 * mode it resolves to the demo league's first team without a backend call.
 */
export function getMyTeam(
  leagueId: string,
  platform: Platform,
): Promise<MyTeamResponse> {
  if (isDemoMode()) return getDemoMyTeam();
  const params = new URLSearchParams({ platform });
  return apiClient.get<MyTeamResponse>(`/leagues/${leagueId}/me?${params}`);
}

/**
 * Save the caller's claimed team. In demo mode nothing is persisted: the call echoes
 * the choice so the page can hold it for the current session only.
 */
export function putMyTeam(
  leagueId: string,
  platform: Platform,
  ownerId: string,
): Promise<MyTeamResponse> {
  if (isDemoMode()) {
    return Promise.resolve({
      detail: 'Saved user preferences',
      data: { owner_id: ownerId },
    });
  }
  const params = new URLSearchParams({ platform });
  return apiClient.put<MyTeamResponse>(`/leagues/${leagueId}/me?${params}`, {
    owner_id: ownerId,
  });
}
