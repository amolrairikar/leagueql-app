import { Trophy } from 'lucide-react';
import { Suspense, use, useMemo, useState } from 'react';
import { CartesianGrid, Line, LineChart, XAxis, YAxis } from 'recharts';

import { getLeague } from '@/components/api/leagues';
import { TeamAvatar } from '@/components/team-avatar';
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from '@/components/ui/chart';
import { Skeleton } from '@/components/ui/skeleton';
import { Switch } from '@/components/ui/switch';
import { getManagerHistoryData } from '@/features/manager_history/api-calls';
import type { ManagerStandingsItem } from '@/features/manager_history/api-calls';
import type { MatchupItem } from '@/features/matchups/api-calls';
import { avatarColor } from '@/lib/color-constants';
import { getLeagueCookies } from '@/lib/cookie-handler';
import { ErrorAlert } from '@/lib/error-alert';
import { toResult, type Result } from '@/lib/result';

interface StatItem {
  label: string;
  value: string;
  sub?: string;
}

interface ChampionItem {
  season: string;
  name: string;
  owner: string;
  record: string;
  pfGame: string;
  highlight?: boolean;
}

function StatsSkeleton() {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 mb-6">
      {Array.from({ length: 4 }).map((_, i) => (
        <div
          key={i}
          className="bg-card border border-border/50 rounded-lg p-3 text-center"
        >
          <Skeleton className="h-3 w-20 mx-auto mb-2" />
          <Skeleton className="h-6 w-12 mx-auto mb-1" />
          <Skeleton className="h-3 w-16 mx-auto" />
        </div>
      ))}
    </div>
  );
}

function ChampionsSkeleton() {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-1.5 mb-6">
      {Array.from({ length: 8 }).map((_, i) => (
        <div
          key={i}
          className="bg-card border border-border/50 rounded-lg p-2.5 flex flex-col gap-0.5"
        >
          <Skeleton className="h-3 w-8 mb-1" />
          <Skeleton className="h-4 w-full mb-0.5" />
          <Skeleton className="h-3 w-16 mb-0.5" />
          <Skeleton className="h-3 w-20" />
        </div>
      ))}
    </div>
  );
}

function AllTimeStandingsSkeleton() {
  return (
    <div className="mb-6">
      <div className="flex items-center justify-between mb-2.5">
        <Skeleton className="h-3 w-32" />
        <Skeleton className="h-5 w-44" />
      </div>
      <div className="bg-card border border-border/50 rounded-lg overflow-hidden">
        {Array.from({ length: 8 }).map((_, i) => (
          <div
            key={i}
            className="flex items-center gap-2 px-3.5 py-2.5 border-b border-border/50 last:border-0"
          >
            <Skeleton className="w-7 h-7 rounded-full shrink-0" />
            <Skeleton className="h-3 w-32" />
            <Skeleton className="h-3 w-16 ml-auto" />
          </div>
        ))}
      </div>
    </div>
  );
}

function LeagueNameHeader({
  promise,
}: {
  promise: Promise<string | undefined>;
}) {
  const leagueName = use(promise);
  return (
    <div className="mb-6">
      <h1 className="text-2xl font-bold text-foreground">
        {leagueName ?? 'League Name'}
      </h1>
    </div>
  );
}

interface ChartDataResult {
  owners: { ownerId: string; username: string }[];
  colorMap: Map<string, string>;
  chartData: Record<string, string | number | null>[];
  chartConfig: ChartConfig;
  maxRank: number;
}

function buildChartData(
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

  const colorMap = new Map(owners.map((o, i) => [o.ownerId, avatarColor(i)]));
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

function StandingsChart({
  standings,
  migrationMapping,
}: {
  standings: ManagerStandingsItem[];
  migrationMapping: Map<string, string>;
}) {
  const [selectedOwnerId, setSelectedOwnerId] = useState<string | null>(null);

  const { owners, colorMap, chartData, chartConfig, maxRank } = useMemo(
    () => buildChartData(standings, migrationMapping),
    [standings, migrationMapping],
  );

  if (standings.length === 0) {
    return (
      <div className="bg-card border border-border/50 rounded-lg p-5">
        <p className="text-[13px] text-muted-foreground text-center py-8">
          No standings data available.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-card border border-border/50 rounded-lg p-5">
      <div className="h-56 w-full">
        <ChartContainer
          config={chartConfig}
          className="h-full w-full aspect-auto"
        >
          <LineChart
            data={chartData}
            margin={{ top: 4, right: 4, left: 0, bottom: 4 }}
          >
            <CartesianGrid vertical={false} />
            <XAxis
              dataKey="season"
              tickLine={false}
              axisLine={false}
              tickMargin={8}
              tick={{ fontSize: 11 }}
            />
            <YAxis
              reversed
              domain={[0.5, maxRank + 0.5]}
              tickLine={false}
              axisLine={false}
              width={28}
              tick={{ fontSize: 11 }}
              tickFormatter={(v: number) => v.toFixed(0)}
            />
            <ChartTooltip
              content={
                <ChartTooltipContent
                  labelFormatter={(label) => `${label}`}
                  indicator="line"
                />
              }
            />
            {owners.map((owner) => {
              const isSelected =
                selectedOwnerId === null || selectedOwnerId === owner.ownerId;
              const opacity =
                selectedOwnerId === null ? 1 : isSelected ? 1 : 0.2;
              return (
                <Line
                  key={owner.ownerId}
                  dataKey={owner.ownerId}
                  stroke={colorMap.get(owner.ownerId)}
                  strokeWidth={2}
                  strokeOpacity={opacity}
                  dot={false}
                  activeDot={{ r: 4 }}
                  type="linear"
                  connectNulls={false}
                />
              );
            })}
          </LineChart>
        </ChartContainer>
      </div>
      <div className="flex flex-wrap gap-4 mt-3">
        {owners.map((owner) => {
          const isSelected =
            selectedOwnerId === null || selectedOwnerId === owner.ownerId;
          const opacity = selectedOwnerId === null ? 1 : isSelected ? 1 : 0.4;
          return (
            <div
              key={owner.ownerId}
              className="flex items-center gap-2 cursor-pointer"
              onClick={() =>
                setSelectedOwnerId(
                  selectedOwnerId === owner.ownerId ? null : owner.ownerId,
                )
              }
              style={{ opacity }}
            >
              <div
                className="w-3 h-3 rounded-sm"
                style={{ backgroundColor: colorMap.get(owner.ownerId) }}
              />
              <span className="text-[11px] text-foreground">
                {owner.username}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

interface AllTimeStandingsData {
  standings: ManagerStandingsItem[];
  matchups: MatchupItem[];
  migrationMapping: Map<string, string>;
}

interface AllTimeRow {
  ownerId: string;
  username: string;
  teamName: string;
  teamLogo: string | null;
  wins: number;
  losses: number;
  ties: number;
  pf: number;
  pa: number;
  games: number;
}

function buildAllTimeStandings(
  standings: ManagerStandingsItem[],
  matchups: MatchupItem[],
  migrationMapping: Map<string, string>,
  mode: 'regular' | 'playoff',
): AllTimeRow[] {
  const remapOwner = (id: string) => migrationMapping.get(id) ?? id;

  // Most recent team identity per owner, for display in the table
  const ownerMeta = new Map<string, ManagerStandingsItem>();
  for (const row of standings) {
    const id = remapOwner(row.owner_id);
    const existing = ownerMeta.get(id);
    if (!existing || row.season.localeCompare(existing.season) > 0) {
      ownerMeta.set(id, row);
    }
  }

  const acc = new Map<string, AllTimeRow>();
  const ensure = (
    ownerId: string,
    fallbackName: string,
    fallbackLogo: string | null,
  ) => {
    let row = acc.get(ownerId);
    if (!row) {
      const meta = ownerMeta.get(ownerId);
      row = {
        ownerId,
        username: meta?.owner_username ?? fallbackName,
        teamName: meta?.team_name ?? '',
        teamLogo: meta?.team_logo ?? fallbackLogo,
        wins: 0,
        losses: 0,
        ties: 0,
        pf: 0,
        pa: 0,
        games: 0,
      };
      acc.set(ownerId, row);
    }
    return row;
  };

  for (const m of matchups) {
    // Playoff standings only count winners' bracket games
    const include =
      mode === 'regular'
        ? m.playoff_tier_type === 'NONE'
        : m.playoff_tier_type === 'WINNERS_BRACKET';
    if (!include) continue;

    const aOwner = remapOwner(m.team_a_primary_owner_id);
    const bOwner = remapOwner(m.team_b_primary_owner_id);
    const aScore = Number(m.team_a_score);
    const bScore = Number(m.team_b_score);

    const a = ensure(aOwner, m.team_a_display_name, m.team_a_team_logo);
    const b = ensure(bOwner, m.team_b_display_name, m.team_b_team_logo);

    a.games++;
    b.games++;
    a.pf += aScore;
    a.pa += bScore;
    b.pf += bScore;
    b.pa += aScore;
    if (aScore > bScore) {
      a.wins++;
      b.losses++;
    } else if (aScore < bScore) {
      a.losses++;
      b.wins++;
    } else {
      a.ties++;
      b.ties++;
    }
  }

  const winPct = (r: AllTimeRow) =>
    r.games > 0 ? (r.wins + 0.5 * r.ties) / r.games : 0;

  return [...acc.values()]
    .filter((r) => r.games > 0)
    .sort((a, b) => b.wins - a.wins || winPct(b) - winPct(a) || b.pf - a.pf);
}

function AllTimeStandingsTable({
  standings,
  matchups,
  migrationMapping,
}: AllTimeStandingsData) {
  const [showPlayoffs, setShowPlayoffs] = useState(false);

  // Owner-stable colors (alphabetical), matching the standings chart below
  const colorMap = useMemo(() => {
    const ownerMeta = new Map<string, ManagerStandingsItem>();
    for (const row of standings) {
      const id = migrationMapping.get(row.owner_id) ?? row.owner_id;
      const existing = ownerMeta.get(id);
      if (!existing || row.season.localeCompare(existing.season) > 0) {
        ownerMeta.set(id, row);
      }
    }
    const sorted = [...ownerMeta.entries()].sort((a, b) =>
      a[1].owner_username.localeCompare(b[1].owner_username),
    );
    return new Map(sorted.map(([id], i) => [id, avatarColor(i)]));
  }, [standings, migrationMapping]);

  const rows = useMemo(
    () =>
      buildAllTimeStandings(
        standings,
        matchups,
        migrationMapping,
        showPlayoffs ? 'playoff' : 'regular',
      ),
    [standings, matchups, migrationMapping, showPlayoffs],
  );

  // Championships per owner (remapped through migration mapping)
  const championshipCounts = useMemo(() => {
    const counts = new Map<string, number>();
    for (const row of standings) {
      if (row.champion === 'Yes') {
        const id = migrationMapping.get(row.owner_id) ?? row.owner_id;
        counts.set(id, (counts.get(id) ?? 0) + 1);
      }
    }
    return counts;
  }, [standings, migrationMapping]);

  return (
    <div className="mb-6">
      <div className="flex items-center justify-between mb-2.5">
        <p className="text-[11px] font-medium uppercase tracking-[0.08em] text-muted-foreground">
          All-time standings
        </p>
        <div className="flex items-center gap-2.5">
          <span
            className={`text-[11px] font-medium ${
              showPlayoffs ? 'text-muted-foreground' : 'text-foreground'
            }`}
          >
            Regular season
          </span>
          <Switch
            checked={showPlayoffs}
            onCheckedChange={setShowPlayoffs}
            aria-label="Toggle between regular season and playoff standings"
          />
          <span
            className={`text-[11px] font-medium ${
              showPlayoffs ? 'text-foreground' : 'text-muted-foreground'
            }`}
          >
            Playoffs
          </span>
        </div>
      </div>

      <div className="bg-card border border-border/50 rounded-lg overflow-hidden">
        <div className="max-h-[70vh] overflow-auto">
          <table
            className="w-full border-collapse text-[13px]"
            style={{ tableLayout: 'fixed', minWidth: '480px' }}
          >
            <thead className="sticky top-0 z-20">
              <tr>
                <th
                  className="text-left text-[10px] font-medium uppercase tracking-[0.07em] text-muted-foreground px-3.5 py-2.5 border-b border-border/50 bg-muted sticky left-0 z-10"
                  style={{ width: '40%' }}
                >
                  Manager
                </th>
                <th
                  className="text-right text-[10px] font-medium uppercase tracking-[0.07em] text-muted-foreground px-3.5 py-2.5 border-b border-border/50 bg-muted"
                  style={{ width: '9%' }}
                >
                  GP
                </th>
                <th
                  className="text-right text-[10px] font-medium uppercase tracking-[0.07em] text-muted-foreground px-3.5 py-2.5 border-b border-border/50 bg-muted"
                  style={{ width: '17%' }}
                >
                  Record
                </th>
                <th
                  className="text-right text-[10px] font-medium uppercase tracking-[0.07em] text-muted-foreground px-3.5 py-2.5 border-b border-border/50 bg-muted"
                  style={{ width: '12%' }}
                >
                  Win %
                </th>
                <th
                  className="text-right text-[10px] font-medium uppercase tracking-[0.07em] text-muted-foreground px-3.5 py-2.5 border-b border-border/50 bg-muted"
                  style={{ width: '11%' }}
                >
                  PF/Game
                </th>
                <th
                  className="text-right text-[10px] font-medium uppercase tracking-[0.07em] text-muted-foreground px-3.5 py-2.5 border-b border-border/50 bg-muted"
                  style={{ width: '11%' }}
                >
                  PA/Game
                </th>
              </tr>
            </thead>
            <tbody>
              {rows.length === 0 ? (
                <tr>
                  <td
                    colSpan={6}
                    className="px-3.5 py-8 text-center text-[13px] text-muted-foreground"
                  >
                    {showPlayoffs
                      ? 'No playoff games available.'
                      : 'No regular season games available.'}
                  </td>
                </tr>
              ) : (
                rows.map((row, i) => {
                  const winPct =
                    row.games > 0 ? (row.wins + 0.5 * row.ties) / row.games : 0;
                  return (
                    <tr
                      key={row.ownerId}
                      className="border-b border-border/50 last:border-0 bg-card"
                    >
                      <td className="px-3.5 py-2.5 sticky left-0 z-10 bg-card">
                        <div className="flex items-center gap-2">
                          <span className="text-[12px] text-muted-foreground w-4 text-right shrink-0">
                            {i + 1}
                          </span>
                          <TeamAvatar
                            teamLogo={row.teamLogo}
                            teamName={row.teamName}
                            ownerUsername={row.username}
                            color={colorMap.get(row.ownerId) ?? avatarColor(i)}
                          />
                          <span className="text-[13px] font-medium text-foreground truncate">
                            {row.username}
                          </span>
                          {(() => {
                            const titles =
                              championshipCounts.get(row.ownerId) ?? 0;
                            if (titles === 0) return null;
                            return (
                              <span
                                className="flex items-center shrink-0"
                                title={`${titles} championship${titles > 1 ? 's' : ''}`}
                                aria-label={`${titles} championship${titles > 1 ? 's' : ''}`}
                              >
                                {Array.from({ length: titles }).map((_, t) => (
                                  <Trophy
                                    key={t}
                                    className="h-3.5 w-3.5 text-yellow-500 fill-yellow-500"
                                  />
                                ))}
                              </span>
                            );
                          })()}
                        </div>
                      </td>
                      <td className="px-3.5 py-2.5 text-right text-muted-foreground">
                        {row.games}
                      </td>
                      <td className="px-3.5 py-2.5 text-right text-muted-foreground">
                        {`${row.wins}-${row.losses}-${row.ties}`}
                      </td>
                      <td className="px-3.5 py-2.5 text-right text-muted-foreground">
                        {winPct.toFixed(3)}
                      </td>
                      <td className="px-3.5 py-2.5 text-right text-muted-foreground">
                        {(row.pf / row.games).toFixed(1)}
                      </td>
                      <td className="px-3.5 py-2.5 text-right text-muted-foreground">
                        {(row.pa / row.games).toFixed(1)}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function ChampionsGrid({ champions }: { champions: ChampionItem[] }) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-1.5 mb-6">
      {champions.map((champ) => (
        <div
          key={champ.season}
          className={`bg-card border border-border/50 rounded-lg p-2.5 flex flex-col gap-0.5 ${
            champ.highlight ? 'border-primary bg-primary/5' : ''
          }`}
        >
          <div className="text-[10px] uppercase tracking-[0.06em] text-muted-foreground">
            {champ.season}
          </div>
          <div className="text-[13px] font-medium text-foreground leading-tight">
            {champ.name}
          </div>
          <div className="text-[11px] text-muted-foreground">{champ.owner}</div>
          <div className="text-[11px] text-muted-foreground">
            {champ.record} · {champ.pfGame} PF/G
          </div>
        </div>
      ))}
    </div>
  );
}

function StatsWithTotalGames({
  stats,
  totalGames,
  champions,
  totalMembers,
}: {
  stats: StatItem[];
  totalGames: number;
  champions: ChampionItem[];
  totalMembers: number;
}) {
  const uniqueChampions = new Set(
    champions.filter((c) => c.owner !== '—').map((c) => c.owner),
  ).size;

  const displayStats = [
    stats[0],
    {
      label: 'Total matchups',
      value: totalGames.toLocaleString(),
    },
    {
      label: 'Total members',
      value: String(totalMembers),
    },
    {
      label: 'Unique champions',
      value: String(uniqueChampions),
    },
  ];
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 mb-6">
      {displayStats.map((stat) => (
        <div
          key={stat.label}
          className="bg-card border border-border/50 rounded-lg p-3 text-center"
        >
          <div className="text-[11px] font-medium uppercase tracking-[0.06em] text-muted-foreground mb-1">
            {stat.label}
          </div>
          <div className="text-[22px] font-medium text-foreground leading-none">
            {stat.value}
          </div>
          <div className="text-[11px] text-muted-foreground mt-0.5">
            {'sub' in stat ? stat.sub : ' '}
          </div>
        </div>
      ))}
    </div>
  );
}

function computeChampions(
  standings: ManagerStandingsItem[],
  seasons: string[],
): ChampionItem[] {
  if (seasons.length === 0) return [];
  const bySeasonMap = new Map<string, ManagerStandingsItem[]>();
  for (const row of standings) {
    if (!bySeasonMap.has(row.season)) bySeasonMap.set(row.season, []);
    bySeasonMap.get(row.season)!.push(row);
  }
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
    return {
      season,
      name: 'TBD',
      owner: '—',
      record: '—',
      pfGame: '—',
      highlight: true,
    };
  });
}

function computeTotalGames(matchups: MatchupItem[], seasons: string[]): number {
  const countBySeason = new Map<string, number>();
  for (const m of matchups) {
    countBySeason.set(m.season, (countBySeason.get(m.season) ?? 0) + 1);
  }
  return seasons.reduce(
    (sum, season) => sum + (countBySeason.get(season) ?? 0),
    0,
  );
}

// A member must appear in matchups, counted on the same remapped owner_id key
// the all-time standings table uses, so the two stay consistent.
function computeTotalMembers(
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

// Stacked skeletons matching the summary layout, shown while the single data
// call resolves.
function SummarySkeleton() {
  return (
    <>
      <StatsSkeleton />
      <p className="text-[11px] font-medium uppercase tracking-[0.08em] text-muted-foreground mb-2.5">
        Champions
      </p>
      <ChampionsSkeleton />
      <AllTimeStandingsSkeleton />
      <p className="text-[11px] font-medium uppercase tracking-[0.08em] text-muted-foreground mb-2.5">
        Final Standings Position by Season
      </p>
      <Skeleton className="h-56 w-full" />
    </>
  );
}

// Consumes the single league-data call. All summary sections derive from this
// one request, so on failure we surface a single inline error in place of the
// (otherwise empty) tables and chart rather than silently rendering blanks.
function LeagueSummary({
  promise,
  stats,
  seasons,
}: {
  promise: Promise<Result<AllTimeStandingsData>>;
  stats: StatItem[];
  seasons: string[];
}) {
  const result = use(promise);
  if (!result.ok) {
    return <ErrorAlert message={result.error} className="my-6" />;
  }
  const { standings, matchups, migrationMapping } = result.data;
  const champions = computeChampions(standings, seasons);
  return (
    <>
      <StatsWithTotalGames
        stats={stats}
        totalGames={computeTotalGames(matchups, seasons)}
        champions={champions}
        totalMembers={computeTotalMembers(matchups, migrationMapping)}
      />
      <p className="text-[11px] font-medium uppercase tracking-[0.08em] text-muted-foreground mb-2.5">
        Champions
      </p>
      <ChampionsGrid champions={champions} />
      <AllTimeStandingsTable
        standings={standings}
        matchups={matchups}
        migrationMapping={migrationMapping}
      />
      <p className="text-[11px] font-medium uppercase tracking-[0.08em] text-muted-foreground mb-2.5">
        Final Standings Position by Season
      </p>
      <StandingsChart
        standings={standings}
        migrationMapping={migrationMapping}
      />
    </>
  );
}

export default function HomePage() {
  const { leagueId, platform, seasons } = useMemo(() => getLeagueCookies(), []);

  const leagueNamePromise = useMemo(
    (): Promise<string | undefined> =>
      leagueId
        ? getLeague(leagueId, platform).then((res) => res.data.league_name)
        : Promise.resolve(undefined),
    [leagueId, platform],
  );

  const stats = useMemo(() => {
    if (seasons.length > 0) {
      const sortedSeasons = seasons.sort();
      const firstSeason = sortedSeasons[0];
      const lastSeason = sortedSeasons[sortedSeasons.length - 1];

      return [
        {
          label: 'Seasons played',
          value: String(seasons.length),
          sub: `${firstSeason} – ${lastSeason}`,
        },
      ];
    }
    return [];
  }, [seasons]);

  // Single API call for all data (getManagerHistoryData already uses optimized
  // single queries). Wrapped in toResult so a failure surfaces inline via
  // LeagueSummary instead of rejecting / showing empty tables.
  const dataResultPromise = useMemo(
    (): Promise<Result<AllTimeStandingsData>> =>
      leagueId && seasons.length > 0
        ? toResult(
            getManagerHistoryData(leagueId, platform, seasons),
            'Failed to load league data.',
          )
        : Promise.resolve({
            ok: true as const,
            data: { standings: [], matchups: [], migrationMapping: new Map() },
          }),
    [leagueId, platform, seasons],
  );

  return (
    <div className="flex flex-1 flex-col p-6 overflow-auto">
      <div className="max-w-225 mx-auto w-full">
        {/* Header */}
        <Suspense
          fallback={
            <div className="mb-6">
              <h1 className="text-2xl font-bold text-foreground">
                League Name
              </h1>
            </div>
          }
        >
          <LeagueNameHeader promise={leagueNamePromise} />
        </Suspense>

        {/* Stats, champions, all-time standings and chart all derive from one call */}
        <Suspense fallback={<SummarySkeleton />}>
          <LeagueSummary
            promise={dataResultPromise}
            stats={stats}
            seasons={seasons}
          />
        </Suspense>
      </div>
    </div>
  );
}
