import type { Platform, MatchupItem, GetLeagueResponse } from './types';

import { apiClient } from '@/lib/api-client';
import { isDemoMode } from '@/lib/cookie-handler';
import { getDemoLeague, queryDemoLeague } from '@/lib/demo-api';

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
  return apiClient.get<{ data: T[] }>(`/leagues/${leagueId}/query?${params}`);
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
