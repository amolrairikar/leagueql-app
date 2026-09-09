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
): Promise<YahooAuthorizeResponse> {
  const params = new URLSearchParams({ leagueId });
  // skipCache: this mints a single-use state server-side, so it must never be deduped.
  return apiClient.get<YahooAuthorizeResponse>(
    `/auth/yahoo/authorize?${params}`,
    undefined,
    { skipCache: true },
  );
}

export interface YahooOnboardResponse {
  detail: string;
  // This increment ships OAuth linking only: a linked Yahoo onboard returns a
  // `YAHOO_COMING_SOON` code rather than a correlation_id (the data client is a follow-up).
  data: { code?: string } | null;
}

/**
 * Onboard a linked Yahoo league. Returns the "coming soon" signal while the Yahoo Fantasy
 * data client is unshipped; a 403 means the link was lost and the user must reconnect.
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
