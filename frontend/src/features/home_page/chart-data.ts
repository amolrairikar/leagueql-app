import { type ChartConfig } from '@/components/ui/chart';
import type { ManagerStandingsItem } from '@/features/manager_history/api-calls';
import { assignAvatarColors, avatarColor } from '@/lib/color-constants';

export interface ChartDataResult {
  owners: { ownerId: string; username: string }[];
  colorMap: Map<string, string>;
  chartData: Record<string, string | number | null>[];
  chartConfig: ChartConfig;
  maxRank: number;
}

export function buildChartData(
  standings: ManagerStandingsItem[],
  migrationMapping: Map<string, string>,
): ChartDataResult {
  const ownerStandingsMap = new Map<string, ManagerStandingsItem[]>();
  for (const row of standings) {
    const mappedId = migrationMapping.get(row.owner_id) ?? row.owner_id;
    if (!ownerStandingsMap.has(mappedId)) ownerStandingsMap.set(mappedId, []);
    ownerStandingsMap.get(mappedId)!.push(row);
  }

  const owners = [...ownerStandingsMap.entries()]
    .map(([ownerId, rows]) => {
      const mostRecent = [...rows].sort((a, b) =>
        b.season.localeCompare(a.season),
      )[0];
      return { ownerId, username: mostRecent.owner_username };
    })
    .sort((a, b) => a.username.localeCompare(b.username));

  const colorMap = assignAvatarColors(owners.map((o) => o.ownerId));
  const allSeasons = [...new Set(standings.map((s) => s.season))].sort();

  const chartData = allSeasons.map((season) => {
    const point: Record<string, string | number | null> = { season };
    for (const { ownerId } of owners) {
      const ownerRows = ownerStandingsMap.get(ownerId) ?? [];
      point[ownerId] =
        ownerRows.find((r) => r.season === season)?.final_rank ?? null;
    }
    return point;
  });

  const chartConfig: ChartConfig = Object.fromEntries(
    owners.map((o, i) => [
      o.ownerId,
      { label: o.username, color: colorMap.get(o.ownerId) ?? avatarColor(i) },
    ]),
  );

  const validRanks = chartData
    .flatMap((d) =>
      Object.entries(d)
        .filter(
          (entry): entry is [string, number | null] => entry[0] !== 'season',
        )
        .map(([, value]) => value),
    )
    .filter((r): r is number => r !== null);
  const maxRank = validRanks.length > 0 ? Math.max(...validRanks) : 12;

  return { owners, colorMap, chartData, chartConfig, maxRank };
}
