import type { Platform } from '@/components/api/types';
import { apiClient } from '@/lib/api-client';

export interface TeamEntry {
  display_name: string;
  primary_owner_id: string;
  team_name: string;
  season: string;
}

export interface EspnMemberEntry {
  owner_id: string;
  display_name: string;
}

export interface SleeperUserEntry {
  user_id: string;
  display_name: string;
  username: string;
}

export interface YahooMemberEntry {
  owner_id: string;
  display_name: string;
}

export interface ManagerMappingEntry {
  currentPlatformOwnerId: string;
  newPlatformOwnerId: string;
  displayName: string;
}

export interface MigrateRequest {
  newPlatformLeagueId: string;
  newPlatform: Platform;
  season?: string;
  s2?: string;
  swid?: string;
  managerMapping: ManagerMappingEntry[];
}

export interface MigrateResponse {
  detail: string;
  data: { correlation_id: string };
}

export function getTeams(
  leagueId: string,
  platform: Platform,
): Promise<{ data: TeamEntry[] }> {
  return apiClient.get<{ data: TeamEntry[] }>(
    `/leagues/${leagueId}/query?${new URLSearchParams({ platform, queryType: 'TEAMS#' })}`,
  );
}

export function getEspnMembers(
  leagueId: string,
  platform: Platform,
  espnLeagueId: string,
  season: string,
  swid: string,
  s2: string,
): Promise<{ data: EspnMemberEntry[] }> {
  const params = new URLSearchParams({ platform, espnLeagueId, season });
  return apiClient.post<{ data: EspnMemberEntry[] }>(
    `/leagues/${leagueId}/espn_members?${params}`,
    { swid, s2 },
  );
}

/**
 * Fetch a destination Yahoo league's managers via the backend proxy (backend/yahoo-members-proxy).
 * The proxy uses the caller's linked Yahoo OAuth token server-side — no token reaches the browser.
 * A `403` means the caller has no valid Yahoo link; callers route that to the OAuth flow.
 */
export function getYahooMembers(
  leagueId: string,
  platform: Platform,
  yahooLeagueId: string,
): Promise<{ data: YahooMemberEntry[] }> {
  const params = new URLSearchParams({ platform, yahooLeagueId });
  return apiClient.post<{ data: YahooMemberEntry[] }>(
    `/leagues/${leagueId}/yahoo_members?${params}`,
    {},
  );
}

export async function getSleeperUsers(
  sleeperLeagueId: string,
): Promise<SleeperUserEntry[]> {
  const res = await fetch(
    `https://api.sleeper.app/v1/league/${sleeperLeagueId}/users`,
  );
  if (!res.ok) {
    throw new Error('Failed to fetch Sleeper league users');
  }
  return res.json() as Promise<SleeperUserEntry[]>;
}

export function migrateLeague(
  leagueId: string,
  platform: Platform,
  body: MigrateRequest,
): Promise<MigrateResponse> {
  return apiClient.post<MigrateResponse>(
    `/leagues/${leagueId}/migrate?${new URLSearchParams({ platform })}`,
    body,
  );
}
