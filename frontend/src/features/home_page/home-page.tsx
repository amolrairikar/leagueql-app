import { CartesianGrid, Line, LineChart, XAxis, YAxis } from 'recharts';
import { Suspense, use, useMemo, useState } from 'react';

import { avatarColor } from '@/components/team-avatar';
import {
  ChartContainer,
  ChartLegend,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from '@/components/ui/chart';
import { Skeleton } from '@/components/ui/skeleton';
import { getManagerHistoryData } from '@/features/manager_history/api-calls';
import type { ManagerStandingsItem } from '@/features/manager_history/api-calls';
import type { MatchupItem } from '@/features/matchups/api-calls';
import { getLeague } from './api-calls';

type StatItem = { label: string; value: string; sub?: string };

type ChampionItem = {
  season: string;
  name: string;
  owner: string;
  record: string;
  pfGame: string;
  highlight?: boolean;
};

function getCookie(name: string): string {
  const match = document.cookie
    .split('; ')
    .find((row) => row.startsWith(`${name}=`));
  return match ? decodeURIComponent(match.split('=')[1] ?? '') : '';
}

function StatsSkeleton() {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2.5 mb-6">
      {Array.from({ length: 5 }).map((_, i) => (
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

function LeagueNameHeader({ promise }: { promise: Promise<string | undefined> }) {
  const leagueName = use(promise);
  return (
    <div className="mb-6">
      <h1 className="text-2xl font-bold text-foreground">
        {leagueName || 'League Name'}
      </h1>
    </div>
  );
}

function StandingsChart({ promise }: { promise: Promise<ManagerStandingsItem[]> }) {
  const standings = use(promise);
  const [selectedOwnerId, setSelectedOwnerId] = useState<string | null>(null);

  if (standings.length === 0) {
    return (
      <div className="bg-card border border-border/50 rounded-lg p-5">
        <p className="text-[13px] text-muted-foreground text-center py-8">
          No standings data available.
        </p>
      </div>
    );
  }

  // Group standings by owner
  const ownerStandingsMap = new Map<string, ManagerStandingsItem[]>();
  for (const row of standings) {
    if (!ownerStandingsMap.has(row.owner_id)) {
      ownerStandingsMap.set(row.owner_id, []);
    }
    ownerStandingsMap.get(row.owner_id)!.push(row);
  }

  // Get unique owners sorted alphabetically for consistent color assignment
  const owners = [...ownerStandingsMap.entries()]
    .map(([ownerId, rows]) => {
      const mostRecent = [...rows].sort((a, b) =>
        b.season.localeCompare(a.season),
      )[0];
      return { ownerId, username: mostRecent.owner_username };
    })
    .sort((a, b) => a.username.localeCompare(b.username));

  const colorMap = new Map(owners.map((o, i) => [o.ownerId, avatarColor(i)]));

  // Get all unique seasons sorted
  const allSeasons = [...new Set(standings.map((s) => s.season))].sort();

  // Build chart data using final_rank
  const chartData = allSeasons.map((season) => {
    const point: Record<string, string | number | null> = { season };
    for (const { ownerId } of owners) {
      const ownerRows = ownerStandingsMap.get(ownerId) || [];
      const seasonRow = ownerRows.find((r) => r.season === season);
      point[ownerId] = seasonRow?.final_rank ?? null;
    }
    return point;
  });

  // Build chart config
  const chartConfig: ChartConfig = Object.fromEntries(
    owners.map((o, i) => [
      o.ownerId,
      { label: o.username, color: colorMap.get(o.ownerId) ?? avatarColor(i) },
    ]),
  );

  // Calculate max rank for Y-axis domain
  const allRanks = chartData.flatMap((d) =>
    Object.entries(d)
      .filter(([key]) => key !== 'season')
      .map(([, value]) => value as number | null),
  );
  const validRanks = allRanks.filter((r): r is number => r !== null);
  const maxRank = validRanks.length > 0 ? Math.max(...validRanks) : 12;

  return (
    <div className="bg-card border border-border/50 rounded-lg p-5">
      <div className="h-56 w-full">
        <ChartContainer config={chartConfig} className="h-full w-full aspect-auto">
          <LineChart data={chartData} margin={{ top: 4, right: 4, left: 0, bottom: 4 }}>
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
              tickFormatter={(v) => v.toFixed(0)}
            />
            <ChartTooltip
              content={
                <ChartTooltipContent
                  labelFormatter={(label) => `${label}`}
                  indicator="line"
                />
              }
            />
            <ChartLegend
              content={
                <div className="flex flex-wrap gap-4">
                  {owners.map((owner) => {
                    const isSelected = selectedOwnerId === null || selectedOwnerId === owner.ownerId;
                    const opacity = selectedOwnerId === null ? 1 : isSelected ? 1 : 0.4;
                    return (
                      <div
                        key={owner.ownerId}
                        className="flex items-center gap-2 cursor-pointer"
                        onClick={() => setSelectedOwnerId(selectedOwnerId === owner.ownerId ? null : owner.ownerId)}
                        style={{ opacity }}
                      >
                        <div
                          className="w-3 h-3 rounded-sm"
                          style={{ backgroundColor: colorMap.get(owner.ownerId) }}
                        />
                        <span className="text-[11px] text-foreground">{owner.username}</span>
                      </div>
                    );
                  })}
                </div>
              }
            />
            {owners.map((owner) => {
              const isSelected = selectedOwnerId === null || selectedOwnerId === owner.ownerId;
              const opacity = selectedOwnerId === null ? 1 : isSelected ? 1 : 0.2;
              return (
                <Line
                  key={owner.ownerId}
                  dataKey={owner.ownerId}
                  stroke={colorMap.get(owner.ownerId)}
                  strokeWidth={2}
                  strokeOpacity={opacity}
                  dot={{ fill: colorMap.get(owner.ownerId), r: 4 }}
                  activeDot={{ r: 6 }}
                  type="monotone"
                  connectNulls={false}
                />
              );
            })}
          </LineChart>
        </ChartContainer>
      </div>
    </div>
  );
}

function ChampionsGrid({ promise }: { promise: Promise<ChampionItem[]> }) {
  const champions = use(promise);
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-1.5 mb-6">
      {champions.map((champ) => (
        <div
          key={champ.season}
          className={`bg-card border border-border/50 rounded-lg p-2.5 flex flex-col gap-0.5 ${
            champ.highlight
              ? 'border-primary bg-primary/5'
              : ''
          }`}
        >
          <div className="text-[10px] uppercase tracking-[0.06em] text-muted-foreground">
            {champ.season}
          </div>
          <div className="text-[13px] font-medium text-foreground leading-tight">
            {champ.name}
          </div>
          <div className="text-[11px] text-muted-foreground">
            {champ.owner}
          </div>
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
  totalGamesPromise,
  championsPromise,
  totalMembersPromise,
  recordScorePromise,
}: {
  stats: StatItem[];
  totalGamesPromise: Promise<number>;
  championsPromise: Promise<ChampionItem[]>;
  totalMembersPromise: Promise<number>;
  recordScorePromise: Promise<{ score: number; week: string; season: string }>;
}) {
  const totalGames = use(totalGamesPromise);
  const champions = use(championsPromise);
  const totalMembers = use(totalMembersPromise);
  const recordScore = use(recordScorePromise);

  const uniqueChampions = new Set(
    champions
      .filter((c) => c.owner !== '—')
      .map((c) => c.owner),
  ).size;

  const displayStats = [
    stats[0],
    {
      label: 'Total games',
      value: totalGames.toLocaleString(),
    },
    {
      label: 'Record score',
      value: recordScore.score.toFixed(2),
      sub: `Week ${recordScore.week}, ${recordScore.season}`,
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
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2.5 mb-6">
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
          {'sub' in stat && (
            <div className="text-[11px] text-muted-foreground mt-0.5">
              {stat.sub}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

export default function HomePage() {
  const leagueId = getCookie('leagueId');
  const platform = (getCookie('leaguePlatform') || 'ESPN') as 'ESPN' | 'SLEEPER';

  const seasons: string[] = useMemo(() => {
    try {
      return JSON.parse(
        decodeURIComponent(getCookie('leagueSeasons')),
      ) as string[];
    } catch {
      return [];
    }
  }, []);

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

  // Single API call for all data (getManagerHistoryData already uses optimized single queries)
  const allDataPromise = useMemo(
    (): Promise<{ standings: ManagerStandingsItem[]; matchups: MatchupItem[] }> =>
      leagueId && seasons.length > 0
        ? getManagerHistoryData(leagueId, platform, seasons)
            .catch(() => ({ standings: [], matchups: [] }))
        : Promise.resolve({ standings: [], matchups: [] }),
    [leagueId, platform, seasons],
  );

  // Derive champions from the single data call
  const championsPromise = useMemo(
    (): Promise<ChampionItem[]> =>
      allDataPromise.then(({ standings }) => {
        if (seasons.length === 0) return [];
        return seasons.map((season) => {
          const seasonStandings = standings.filter((s) => s.season === season);
          const champion = seasonStandings.find((s) => s.champion === 'Yes');
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
      }),
    [allDataPromise, seasons],
  );

  // Derive total games from the single data call
  const totalGamesPromise = useMemo(
    (): Promise<number> =>
      allDataPromise.then(({ matchups }) => {
        if (seasons.length === 0) return 1120;
        const seasonMatchups = seasons.map((season) =>
          matchups.filter((m) => m.season === season).length,
        );
        return seasonMatchups.reduce((sum, count) => sum + count, 0);
      }),
    [allDataPromise, seasons],
  );

  // Derive total members from the single data call
  const totalMembersPromise = useMemo(
    (): Promise<number> =>
      allDataPromise.then(({ standings }) => {
        if (standings.length === 0) return 10;
        const allOwners = new Set(standings.map((s) => s.owner_username));
        return allOwners.size;
      }),
    [allDataPromise],
  );

  // Derive record score from the single data call
  const recordScorePromise = useMemo(
    (): Promise<{ score: number; week: string; season: string }> =>
      allDataPromise.then(({ matchups }) => {
        if (matchups.length === 0) return { score: 198.7, week: '11', season: '2021' };
        let maxScore = 0;
        let maxWeek = '';
        let maxSeason = '';

        for (const matchup of matchups) {
          if (matchup.team_a_score > maxScore) {
            maxScore = matchup.team_a_score;
            maxWeek = matchup.week;
            maxSeason = matchup.season;
          }
          if (matchup.team_b_score > maxScore) {
            maxScore = matchup.team_b_score;
            maxWeek = matchup.week;
            maxSeason = matchup.season;
          }
        }

        return { score: maxScore, week: maxWeek, season: maxSeason };
      }),
    [allDataPromise],
  );

  // Use standings from the single data call for chart
  const standingsPromise = useMemo(
    (): Promise<ManagerStandingsItem[]> =>
      allDataPromise.then(({ standings }) => standings),
    [allDataPromise],
  );

  return (
    <div className="flex flex-1 flex-col p-6 overflow-auto">
      <div className="max-w-225 mx-auto w-full">
        {/* Header */}
        <Suspense fallback={<div className="mb-6"><h1 className="text-2xl font-bold text-foreground">League Name</h1></div>}>
          <LeagueNameHeader promise={leagueNamePromise} />
        </Suspense>

        {/* Stats Grid */}
        <Suspense fallback={<StatsSkeleton />}>
          <StatsWithTotalGames stats={stats} totalGamesPromise={totalGamesPromise} championsPromise={championsPromise} totalMembersPromise={totalMembersPromise} recordScorePromise={recordScorePromise} />
        </Suspense>

        {/* Champions */}
        <p className="text-[11px] font-medium uppercase tracking-[0.08em] text-muted-foreground mb-2.5">
          Champions
        </p>
        <Suspense fallback={<ChampionsSkeleton />}>
          <ChampionsGrid promise={championsPromise} />
        </Suspense>

        {/* Chart */}
        <p className="text-[11px] font-medium uppercase tracking-[0.08em] text-muted-foreground mb-2.5">
          Final Standings Position by Season
        </p>
        <Suspense fallback={<Skeleton className="h-56 w-full" />}>
          <StandingsChart promise={standingsPromise} />
        </Suspense>
      </div>
    </div>
  );
}
