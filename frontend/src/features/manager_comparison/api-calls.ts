import { apiClient } from '@/lib/api-client';
import { isDemoMode } from '@/lib/cookie-handler';
import { queryDemoLeague } from '@/lib/demo-api';
import type { Platform, MatchupItem } from '@/components/api/types';
import type { PlatformMigrationEntry } from '@/features/manager_history/api-calls';

export type { MatchupItem };

export async function getAllSeasonsMatchups(
  leagueId: string,
  platform: Platform,
): Promise<{ matchups: MatchupItem[]; migrationMapping: Map<string, string> }> {
  if (isDemoMode()) {
    const [matchupsRes, migrationRes] = await Promise.all([
      queryDemoLeague<MatchupItem>('MATCHUPS#'),
      queryDemoLeague<PlatformMigrationEntry>('PLATFORM_MIGRATION'),
    ]);
    const migrationMapping = new Map<string, string>(
      migrationRes.data.map((e) => [
        e.current_platform_owner_id,
        e.new_platform_owner_id,
      ]),
    );
    return { matchups: matchupsRes.data, migrationMapping };
  }

  const [matchups, migrationResult] = await Promise.all([
    apiClient
      .get<{
        data: MatchupItem[];
      }>(
        `/leagues/${leagueId}/query?${new URLSearchParams({ platform, queryType: 'MATCHUPS#' })}`,
      )
      .then((res) => res.data),
    apiClient
      .get<{ data: PlatformMigrationEntry[] }>(
        `/leagues/${leagueId}/query?${new URLSearchParams({ platform, queryType: 'PLATFORM_MIGRATION' })}`,
      )
      .then((r) => r.data)
      .catch(() => [] as PlatformMigrationEntry[]),
  ]);
  const migrationMapping = new Map<string, string>(
    migrationResult.map((e) => [
      e.current_platform_owner_id,
      e.new_platform_owner_id,
    ]),
  );
  return { matchups, migrationMapping };
}
