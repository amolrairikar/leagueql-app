import type { ManagerStandingsItem } from '@/features/manager_history/api-calls';
import type { MatchupItem } from '@/features/matchups/api-calls';
import { isUnplayedMatchup } from '@/lib/matchups';

export interface StatItem {
  label: string;
  value: string;
  sub?: string;
}

export interface ChampionItem {
  season: string;
  name: string;
  owner: string;
  record: string;
  pfGame: string;
  highlight?: boolean;
}

export function computeChampions(
  standings: ManagerStandingsItem[],
  seasons: string[],
): ChampionItem[] {
  if (seasons.length === 0) return [];
  const bySeasonMap = new Map<string, ManagerStandingsItem[]>();
  for (const row of standings) {
    if (!bySeasonMap.has(row.season)) bySeasonMap.set(row.season, []);
    bySeasonMap.get(row.season)!.push(row);
  }
  // Only the most recent season can legitimately still be in progress (playoffs not yet
  // decided) → "TBD". Any earlier season is complete, so a missing champion there is a
  // finished season with no recorded title → "N/A", not a pending one.
  const latestSeason = seasons.reduce(
    (latest, season) => (season > latest ? season : latest),
    seasons[0],
  );
  return seasons.map((season) => {
    const champion = bySeasonMap.get(season)?.find((s) => s.champion === 'Yes');
    if (champion) {
      return {
        season,
        name: champion.team_name || `Team ${champion.owner_username}`,
        owner: champion.owner_username,
        record: champion.record,
        pfGame: champion.avg_pf.toFixed(1),
      };
    }
    const inProgress = season === latestSeason;
    return {
      season,
      name: inProgress ? 'TBD' : 'N/A',
      owner: '—',
      record: '—',
      pfGame: '—',
      highlight: inProgress,
    };
  });
}

export function computeTotalGames(
  matchups: MatchupItem[],
  seasons: string[],
): number {
  const countBySeason = new Map<string, number>();
  for (const m of matchups) {
    // Unplayed 0-0 placeholder weeks are not games played.
    if (isUnplayedMatchup(m)) continue;
    countBySeason.set(m.season, (countBySeason.get(m.season) ?? 0) + 1);
  }
  return seasons.reduce(
    (sum, season) => sum + (countBySeason.get(season) ?? 0),
    0,
  );
}

// A member must appear in matchups, counted on the same remapped owner_id key
// the all-time standings table uses, so the two stay consistent.
export function computeTotalMembers(
  matchups: MatchupItem[],
  migrationMapping: Map<string, string>,
): number {
  const remapOwner = (id: string) => migrationMapping.get(id) ?? id;
  const owners = new Set<string>();
  for (const m of matchups) {
    owners.add(remapOwner(m.team_a_primary_owner_id));
    owners.add(remapOwner(m.team_b_primary_owner_id));
  }
  return owners.size;
}
