import type { MatchupItem } from '@/features/matchups/api-calls';
import { apiClient } from '@/lib/api-client';

export type { MatchupItem };

export interface ManagerStandingsItem {
  season: string;
  team_id: string;
  owner_id: string;
  team_name: string;
  team_logo: string | null;
  owner_username: string;
  final_rank: number | null;
  games_played: number;
  wins: number;
  losses: number;
  ties: number;
  record: string;
  total_pf: number;
  avg_pf: number;
  champion: string;
}

export interface ManagerRecapItem {
  owner_id: string;
  owner_username: string;
  recap_text: string;
  generated_at: string;
}

export async function getManagerHistoryData(
  leagueId: string,
  platform: 'ESPN' | 'SLEEPER',
  seasons: string[],
): Promise<{
  standings: ManagerStandingsItem[];
  matchups: MatchupItem[];
  managerRecaps: Record<string, string>;
}> {
  const [standingsResults, matchupResults] = await Promise.all([
    Promise.all(
      seasons.map((season) =>
        apiClient
          .get<{
            data: ManagerStandingsItem[];
          }>(
            `/leagues/${leagueId}/query?${new URLSearchParams({ platform, queryType: `SEASON_STANDINGS#${season}` })}`,
          )
          .then((r) => r.data),
      ),
    ),
    Promise.all(
      seasons.map((season) =>
        apiClient
          .get<{
            data: MatchupItem[];
          }>(
            `/leagues/${leagueId}/query?${new URLSearchParams({ platform, queryType: `MATCHUPS#${season}#` })}`,
          )
          .then((r) => r.data),
      ),
    ),
  ]);

  const standings = standingsResults.flat();
  const matchups = matchupResults.flat();

  const ownerIds = [...new Set(standings.map((s) => s.owner_id))];

  const recapResults = await Promise.all(
    ownerIds.map((ownerId) =>
      apiClient
        .get<{ data: ManagerRecapItem[] }>(
          `/leagues/${leagueId}/query?${new URLSearchParams({ platform, queryType: `AI_RECAP#MANAGER#${ownerId}` })}`,
        )
        .then((r) => ({ ownerId, items: r.data }))
        .catch(() => ({ ownerId, items: [] as ManagerRecapItem[] })),
    ),
  );

  const managerRecaps: Record<string, string> = {};
  for (const { ownerId, items } of recapResults) {
    if (items.length > 0 && items[0]) {
      managerRecaps[ownerId] = items[0].recap_text;
    }
  }

  return { standings, matchups, managerRecaps };
}
