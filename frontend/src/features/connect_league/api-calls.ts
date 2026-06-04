import type { Platform } from '@/components/api/types';
import { apiClient } from '@/lib/api-client';

export interface GetJobStatusResponse {
  detail: string;
  data: {
    status: string;
    failure_code?: string | null;
    failure_reason?: string | null;
  };
}

export function getJobStatus(jobId: string): Promise<GetJobStatusResponse> {
  // Bypass the client-side GET cache so each poll reflects the live job status
  // (the cache would otherwise serve a stale IN_PROGRESS for up to 30s).
  return apiClient.get<GetJobStatusResponse>(`/jobs/${jobId}`, undefined, {
    skipCache: true,
  });
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
