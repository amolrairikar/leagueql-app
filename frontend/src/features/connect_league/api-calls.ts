import { apiClient } from '@/lib/api-client';
import type { Platform } from '@/components/api/types';

export interface GetRefreshStatusResponse {
  detail: string;
  data: {
    refresh_operation: 'ONBOARD' | 'REFRESH';
    refresh_status: string;
  };
}

export function getRefreshStatus(
  leagueId: string,
  platform: Platform,
  refreshOperation: 'ONBOARD' | 'REFRESH' | 'MIGRATE',
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
  data: { correlation_id: string };
}

export function onboardLeague(
  requestType: 'ONBOARD' | 'REFRESH',
  body: OnboardRequest,
): Promise<OnboardResponse> {
  const params = new URLSearchParams({ requestType });
  return apiClient.post<OnboardResponse>(`/leagues?${params}`, body);
}
