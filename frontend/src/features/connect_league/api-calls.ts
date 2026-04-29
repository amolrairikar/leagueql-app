import { apiClient } from '@/lib/api-client';
import type { Platform } from '@/components/api/types';

export type { GetLeagueResponse } from '@/components/api/types';
export { getLeague } from '@/components/api/leagues';

export interface GetRefreshStatusResponse {
  detail: string;
  data: {
    canonical_league_id: string;
    refresh_operation: 'ONBOARD' | 'REFRESH';
    refresh_status: string;
  };
}

export function getRefreshStatus(
  leagueId: string,
  platform: Platform,
  refreshOperation: 'ONBOARD' | 'REFRESH',
): Promise<GetRefreshStatusResponse> {
  const params = new URLSearchParams({ platform, refreshOperation });
  return apiClient.get<GetRefreshStatusResponse>(
    `/leagues/${leagueId}/refresh_status?${params}`,
  );
}

export interface OnboardRequest {
  leagueId: string;
  platform: Platform;
  season?: string;
  s2?: string;
  swid?: string;
}

export interface OnboardResponse {
  detail: string;
}

export function onboardLeague(
  requestType: 'ONBOARD' | 'REFRESH',
  body: OnboardRequest,
): Promise<OnboardResponse> {
  const params = new URLSearchParams({ requestType });
  return apiClient.post<OnboardResponse>(`/leagues?${params}`, body);
}
