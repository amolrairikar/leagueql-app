import type { Platform, MatchupItem, GetLeagueResponse } from './types';

import { apiClient } from '@/lib/api-client';
import { isDemoMode } from '@/lib/cookie-handler';
import { getDemoLeague, queryDemoLeague } from '@/lib/demo-api';

// Precomputed views only change when a league is onboarded/refreshed (which
// clears the cache), so they can be cached far longer than the 30s default.
const QUERY_CACHE_TTL_MS = 5 * 60 * 1000;

/**
 * Shared accessor for the `/leagues/{id}/query` endpoint.
 *
 * In demo mode it resolves against the local demo dataset; otherwise it issues
 * the real GET with `platform` + `queryType` params. Every feature that reads
 * league data goes through here so the demo-mode branch, query string shape and
 * response envelope live in exactly one place.
 */
export function queryLeague<T>(
  leagueId: string,
  platform: Platform,
  queryType: string,
): Promise<{ data: T[] }> {
  if (isDemoMode()) return queryDemoLeague<T>(queryType);
  const params = new URLSearchParams({ platform, queryType });
  return apiClient.get<{ data: T[] }>(
    `/leagues/${leagueId}/query?${params}`,
    undefined,
    { cacheTtlMs: QUERY_CACHE_TTL_MS },
  );
}

export interface PlatformMigrationEntry {
  current_platform_owner_id: string;
  new_platform_owner_id: string;
  display_name: string;
}

/**
 * Builds the owner-id remapping for leagues that migrated platforms.
 * Maps each `current_platform_owner_id` → `new_platform_owner_id`.
 * Returns an empty map if the league has no migration history.
 */
export async function getMigrationMapping(
  leagueId: string,
  platform: Platform,
): Promise<Map<string, string>> {
  // A league with no migration history legitimately 404s here; this is a
  // best-effort enrichment query, so any failure falls back to an empty mapping.
  const entries = await queryLeague<PlatformMigrationEntry>(
    leagueId,
    platform,
    'PLATFORM_MIGRATION',
  )
    .then((r) => r.data)
    .catch(() => [] as PlatformMigrationEntry[]);
  return new Map(
    entries.map((e) => [e.current_platform_owner_id, e.new_platform_owner_id]),
  );
}

export function getLeague(
  leagueId: string,
  platform: Platform,
): Promise<GetLeagueResponse> {
  if (isDemoMode()) return getDemoLeague();
  const params = new URLSearchParams({ platform });
  return apiClient.get<GetLeagueResponse>(`/leagues/${leagueId}?${params}`);
}

export function getAllMatchups(
  leagueId: string,
  platform: Platform,
): Promise<{ data: MatchupItem[] }> {
  return queryLeague<MatchupItem>(leagueId, platform, 'MATCHUPS#');
}

/**
 * Verify the caller's ESPN league membership (backend/league-authorization / frontend/ownership-transfer).
 *
 * Sends the caller's ESPN cookies (filled by the Chrome extension) to the
 * backend, which proxies an authenticated read of the league. On success the
 * caller is added to the league's members and may read the league. ESPN-rejected
 * cookies resolve to a `403` `ApiError`.
 */
export function verifyMembership(
  leagueId: string,
  platform: Platform,
  cookies: { swid: string; s2: string },
): Promise<{ detail: string }> {
  const params = new URLSearchParams({ platform });
  return apiClient.post<{ detail: string }>(
    `/leagues/${leagueId}/verify-membership?${params}`,
    cookies,
  );
}

export interface TransferTokenResponse {
  detail: string;
  data: { token: string; expires_at: string };
}

/** Mint a one-time ownership-transfer token for the league (owner-only). */
export function createTransferToken(
  leagueId: string,
  platform: Platform,
): Promise<TransferTokenResponse> {
  const params = new URLSearchParams({ platform });
  return apiClient.post<TransferTokenResponse>(
    `/leagues/${leagueId}/transfer-token?${params}`,
    {},
  );
}

/** Redeem a transfer token to become the league owner. */
export function claimOwnership(
  leagueId: string,
  platform: Platform,
  token: string,
): Promise<{ detail: string }> {
  const params = new URLSearchParams({ platform });
  return apiClient.post<{ detail: string }>(
    `/leagues/${leagueId}/claim-ownership?${params}`,
    { token },
  );
}
