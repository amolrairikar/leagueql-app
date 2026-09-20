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

export interface YahooAuthorizeResponse {
  detail: string;
  data: { authorize_url: string };
}

/**
 * Start the Yahoo OAuth link (backend/yahoo-oauth). Returns the Yahoo consent URL the
 * caller full-page-redirects to; the pending `leagueId` is carried through the flow so the
 * callback can resume onboarding. No Yahoo tokens ever reach the browser.
 */
export function getYahooAuthorizeUrl(
  leagueId: string,
  flow?: 'ONBOARD' | 'MIGRATE',
): Promise<YahooAuthorizeResponse> {
  const params = new URLSearchParams({ leagueId });
  if (flow) params.set('flow', flow);
  // skipCache: this mints a single-use state server-side, so it must never be deduped.
  return apiClient.get<YahooAuthorizeResponse>(
    `/leagues/yahoo/oauth/authorize?${params}`,
    undefined,
    { skipCache: true },
  );
}

export interface YahooOnboardResponse {
  detail: string;
  // A league that is already onboarded returns 200 with a null `data` ("League already
  // onboarded"); a fresh onboard returns a `correlation_id` to poll.
  data: { correlation_id: string } | null;
}

/**
 * Onboard a linked Yahoo league. A fresh onboard returns a `correlation_id` the caller polls
 * to completion (the same async flow as ESPN/Sleeper); an already-onboarded league returns a
 * null `data` so the caller can route straight into the existing league. A 403 means the link
 * was lost and the user must reconnect. No Yahoo tokens ever reach the browser.
 */
export function onboardYahooLeague(
  leagueId: string,
): Promise<YahooOnboardResponse> {
  const params = new URLSearchParams({ requestType: 'ONBOARD' });
  return apiClient.post<YahooOnboardResponse>(`/leagues?${params}`, {
    leagueId,
    platform: 'YAHOO',
  });
}
