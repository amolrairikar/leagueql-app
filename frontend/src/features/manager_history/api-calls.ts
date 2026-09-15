import { queryLeague, getMigrationMapping } from '@/components/api/leagues';
import type { Platform, MatchupItem } from '@/components/api/types';

export type { MatchupItem };
export type { PlatformMigrationEntry } from '@/components/api/leagues';

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

/**
 * Fill in `final_rank` for an in-progress season.
 *
 * A finalized season carries a real `final_rank` per team (ESPN's
 * `rankCalculatedFinal`; Sleeper's bracket placement). A season still in
 * progress has none yet — ESPN reports `rankCalculatedFinal` as `0` and Sleeper
 * leaves it `null` until the playoff bracket resolves — which would otherwise
 * plot everyone at rank `0` (or nothing) on the standings-position views.
 *
 * For such a season (no team has a finalized placement) that has games played,
 * derive each team's *current* standings position from the regular-season
 * record, ordering by wins then points-for — the same canonical order the
 * backend `SEASON_STANDINGS` view uses (`ORDER BY ... wins DESC, total_pf DESC`).
 * A season with no games yet keeps a `null` `final_rank` (nothing to rank).
 */
function withInProgressRanks(
  standings: ManagerStandingsItem[],
): ManagerStandingsItem[] {
  const bySeason = new Map<string, ManagerStandingsItem[]>();
  for (const row of standings) {
    const rows = bySeason.get(row.season);
    if (rows) rows.push(row);
    else bySeason.set(row.season, [row]);
  }

  // Provisional current-standings rank per in-progress team, keyed season|team.
  const provisionalRank = new Map<string, number>();
  for (const [season, rows] of bySeason) {
    const isFinalized = rows.some(
      (r) => r.final_rank != null && r.final_rank >= 1,
    );
    const hasGames = rows.some((r) => r.games_played > 0);
    if (isFinalized || !hasGames) continue;
    [...rows]
      .sort((a, b) => b.wins - a.wins || b.total_pf - a.total_pf)
      .forEach((r, i) => provisionalRank.set(`${season}|${r.team_id}`, i + 1));
  }

  return standings.map((r) => {
    const provisional = provisionalRank.get(`${r.season}|${r.team_id}`);
    if (provisional != null) return { ...r, final_rank: provisional };
    // Otherwise normalize a non-positive `final_rank` (ESPN's `0` for a season
    // with no games yet) to `null` so an unfinalized season is never plotted at
    // rank `0`.
    return r.final_rank != null && r.final_rank < 1
      ? { ...r, final_rank: null }
      : r;
  });
}

export async function getManagerHistoryData(
  leagueId: string,
  platform: Platform,
  seasons: string[],
): Promise<{
  standings: ManagerStandingsItem[];
  matchups: MatchupItem[];
  migrationMapping: Map<string, string>;
}> {
  const [standingsResult, matchupResult, migrationMapping] = await Promise.all([
    queryLeague<ManagerStandingsItem>(
      leagueId,
      platform,
      'SEASON_STANDINGS#',
    ).then((r) => r.data),
    queryLeague<MatchupItem>(leagueId, platform, 'MATCHUPS#').then(
      (r) => r.data,
    ),
    getMigrationMapping(leagueId, platform),
  ]);

  const standings = withInProgressRanks(
    standingsResult.filter((s) => seasons.includes(s.season)),
  );
  const matchups = matchupResult.filter((m) => seasons.includes(m.season));

  return { standings, matchups, migrationMapping };
}
