import { apiClient } from '@/lib/api-client';
import type { Platform } from '@/components/api/types';

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

export interface ManagerMappingEntry {
  currentPlatformOwnerId: string;
  newPlatformOwnerId: string;
  displayName: string;
}

export interface MigrateRequest {
  newPlatformLeagueId: string;
  newPlatform: 'ESPN' | 'SLEEPER';
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
  const params = new URLSearchParams({ espnLeagueId, season });
  return apiClient.post<{ data: EspnMemberEntry[] }>(
    `/leagues/${leagueId}/espn_members?${params}`,
    { swid, s2 },
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
