import { apiClient } from '@/lib/api-client';

export interface GetLeagueResponse {
  detail: string;
  data: {
    canonical_league_id: string;
    seasons: string[];
  };
}

export function getLeague(
  leagueId: string,
  platform: 'ESPN' | 'SLEEPER',
): Promise<GetLeagueResponse> {
  const params = new URLSearchParams({ platform });
  return apiClient.get<GetLeagueResponse>(`/leagues/${leagueId}?${params}`);
}

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
  platform: 'ESPN' | 'SLEEPER',
  refreshOperation: 'ONBOARD' | 'REFRESH',
): Promise<GetRefreshStatusResponse> {
  const params = new URLSearchParams({ platform, refreshOperation });
  return apiClient.get<GetRefreshStatusResponse>(
    `/leagues/${leagueId}/refresh_status?${params}`,
  );
}

export interface OnboardRequest {
  leagueId: string;
  platform: 'ESPN' | 'SLEEPER';
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
