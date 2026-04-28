import { Info } from 'lucide-react';
import { Suspense, use, useMemo, useState } from 'react';
import { CartesianGrid, Line, LineChart, XAxis, YAxis } from 'recharts';

import { avatarColor } from '@/components/team-avatar';
import {
  ChartContainer,
  ChartTooltip,
  type ChartConfig,
} from '@/components/ui/chart';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import {
  getManagerHistoryData,
  type ManagerStandingsItem,
  type MatchupItem,
} from '@/features/manager_history/api-calls';

// ── Types ─────────────────────────────────────────────────────────────────────

interface SeasonEntry {
  year: string;
  team: string;
  record: string;
  pts: number;
  avg: number;
  high: number;
  result: 'champion' | 'runner' | 'playoff' | 'elim';
  finish: number | null;
}

interface RivalryEntry {
  oppId: string;
  oppName: string;
  oppTeam: string;
  oppColor: string;
  oppInit: string;
  w: number;
  l: number;
  avgFor: number;
  avgAgainst: number;
  lastResult: 'W' | 'L';
}

interface ManagerData {
  owner_id: string;
  owner_username: string;
  init: string;
  color: string;
  currentTeam: string;
  allTime: {
    wins: number;
    losses: number;
    championships: number;
    playoffs: number;
    highScore: number;
    avgPts: number;
  };
  seasons: SeasonEntry[];
  rivalries: RivalryEntry[];
}

type DataResult =
  | { ok: true; data: ManagerData[] }
  | { ok: false; error: string };

interface RivalryAcc {
  w: number;
  l: number;
  totalFor: number;
  totalAgainst: number;
  count: number;
  lastSeason: string;
  lastWeek: number;
  lastWon: boolean;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function getCookie(name: string): string {
  const match = document.cookie
    .split('; ')
    .find((row) => row.startsWith(`${name}=`));
  return match ? decodeURIComponent(match.split('=')[1] ?? '') : '';
}

function managerInitials(username: string): string {
  const parts = username
    .replace(/[^a-zA-Z0-9]/g, ' ')
    .trim()
    .split(/\s+/)
    .filter(Boolean);
  if (parts.length >= 2)
    return ((parts[0]?.[0] ?? '') + (parts[1]?.[0] ?? '')).toUpperCase();
  return username.slice(0, 2).toUpperCase();
}

function resultBadge(result: string) {
  if (result === 'champion')
    return (
      <span
        className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-medium"
        style={{ background: '#EEEDFE', color: '#3C3489' }}
      >
        Champion
      </span>
    );
  if (result === 'runner')
    return (
      <span
        className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-medium"
        style={{ background: '#FAEEDA', color: '#633806' }}
      >
        Runner-up
      </span>
    );
  if (result === 'playoff')
    return (
      <span
        className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-medium"
        style={{ background: '#E1F5EE', color: '#085041' }}
      >
        Playoffs
      </span>
    );
  return (
    <span
      className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-medium"
      style={{ background: '#F1EFE8', color: '#444441' }}
    >
      <span className="whitespace-nowrap">Missed Playoffs</span>
    </span>
  );
}

function ordinal(n: number) {
  const s = ['th', 'st', 'nd', 'rd'],
    v = n % 100;
  return n + (s[(v - 20) % 10] || s[v] || s[0]);
}

function pct(a: number, b: number) {
  const t = a + b;
  return t === 0 ? 50 : Math.round((a / t) * 100);
}

// ── Data processing ───────────────────────────────────────────────────────────

function processData(
  standings: ManagerStandingsItem[],
  matchups: MatchupItem[],
): ManagerData[] {
  const ownerStandingsMap = new Map<string, ManagerStandingsItem[]>();
  for (const row of standings) {
    if (!ownerStandingsMap.has(row.owner_id))
      ownerStandingsMap.set(row.owner_id, []);
    ownerStandingsMap.get(row.owner_id)!.push(row);
  }

  const highScoreMap = new Map<string, Map<string, number>>();
  const playoffMap = new Map<string, Set<string>>();
  const runnerUpMap = new Map<string, Set<string>>();

  const rivalryMap = new Map<string, Map<string, RivalryAcc>>();

  for (const m of matchups) {
    const aOwner = m.team_a_primary_owner_id;
    const bOwner = m.team_b_primary_owner_id;
    const { season } = m;
    const week = parseInt(m.week, 10);
    const aScore = Number(m.team_a_score);
    const bScore = Number(m.team_b_score);

    // High scores per owner per season
    for (const [owner, score] of [
      [aOwner, aScore],
      [bOwner, bScore],
    ] as [string, number][]) {
      if (!highScoreMap.has(owner)) highScoreMap.set(owner, new Map());
      const prev = highScoreMap.get(owner)!.get(season) ?? 0;
      if (score > prev) highScoreMap.get(owner)!.set(season, score);
    }

    // Playoff appearances and runner-up detection
    if (m.playoff_tier_type === 'WINNERS_BRACKET') {
      for (const owner of [aOwner, bOwner]) {
        if (!playoffMap.has(owner)) playoffMap.set(owner, new Set());
        playoffMap.get(owner)!.add(season);
      }
      if (m.playoff_round === 'Finals' && m.loser !== 'TIE' && m.loser !== '') {
        const loserOwner = m.loser === m.team_a_id ? aOwner : bOwner;
        if (!runnerUpMap.has(season)) runnerUpMap.set(season, new Set());
        runnerUpMap.get(season)!.add(loserOwner);
      }
    }

    // Head-to-head rivalry data across all matchups
    for (const [owner, opp, ownerScore, oppScore] of [
      [aOwner, bOwner, aScore, bScore],
      [bOwner, aOwner, bScore, aScore],
    ] as [string, string, number, number][]) {
      if (!rivalryMap.has(owner)) rivalryMap.set(owner, new Map());
      const oppMap = rivalryMap.get(owner)!;
      if (!oppMap.has(opp)) {
        oppMap.set(opp, {
          w: 0,
          l: 0,
          totalFor: 0,
          totalAgainst: 0,
          count: 0,
          lastSeason: '',
          lastWeek: 0,
          lastWon: false,
        });
      }
      const r = oppMap.get(opp)!;
      r.count++;
      r.totalFor += ownerScore;
      r.totalAgainst += oppScore;
      if (ownerScore > oppScore) r.w++;
      else if (ownerScore < oppScore) r.l++;
      if (
        season > r.lastSeason ||
        (season === r.lastSeason && week > r.lastWeek)
      ) {
        r.lastSeason = season;
        r.lastWeek = week;
        r.lastWon = ownerScore > oppScore;
      }
    }
  }

  // Sort owners alphabetically to get consistent color assignment
  const owners = [...ownerStandingsMap.entries()]
    .map(([ownerId, rows]) => {
      const mostRecent = [...rows].sort((a, b) =>
        b.season.localeCompare(a.season),
      )[0];
      return { ownerId, username: mostRecent.owner_username };
    })
    .sort((a, b) => a.username.localeCompare(b.username));

  const colorMap = new Map(owners.map((o, i) => [o.ownerId, avatarColor(i)]));

  const ownerUsernames = new Map<string, string>();
  const ownerCurrentTeams = new Map<string, string>();
  for (const [ownerId, rows] of ownerStandingsMap) {
    const mostRecent = [...rows].sort((a, b) =>
      b.season.localeCompare(a.season),
    )[0];
    ownerUsernames.set(ownerId, mostRecent.owner_username);
    ownerCurrentTeams.set(ownerId, mostRecent.team_name);
  }

  return owners.map(({ ownerId }, colorIdx) => {
    const rows = ownerStandingsMap.get(ownerId)!;
    const mostRecent = [...rows].sort((a, b) =>
      b.season.localeCompare(a.season),
    )[0];

    const allWins = rows.reduce((s, r) => s + r.wins, 0);
    const allLosses = rows.reduce((s, r) => s + r.losses, 0);
    const championships = rows.filter((r) => r.champion === 'Yes').length;
    const playoffs = playoffMap.get(ownerId)?.size ?? 0;

    const ownerHighs = highScoreMap.get(ownerId);
    const allTimeHigh =
      ownerHighs && ownerHighs.size > 0 ? Math.max(...ownerHighs.values()) : 0;

    const totalPf = rows.reduce((s, r) => s + r.total_pf, 0);
    const totalGames = rows.reduce((s, r) => s + r.games_played, 0);
    const avgPts = totalGames > 0 ? totalPf / totalGames : 0;

    const seasons: SeasonEntry[] = rows
      .map((r) => {
        const isChampion = r.champion === 'Yes';
        const isRunnerUp = runnerUpMap.get(r.season)?.has(ownerId) ?? false;
        const madePlayoffs = playoffMap.get(ownerId)?.has(r.season) ?? false;

        let result: 'champion' | 'runner' | 'playoff' | 'elim';
        if (isChampion) result = 'champion';
        else if (isRunnerUp) result = 'runner';
        else if (madePlayoffs) result = 'playoff';
        else result = 'elim';

        let finish: number | null = r.final_rank ?? null;
        if (finish === null) {
          if (isChampion) finish = 1;
          else if (isRunnerUp) finish = 2;
        }

        return {
          year: r.season,
          team: r.team_name,
          record: r.record,
          pts: r.total_pf,
          avg: r.avg_pf,
          high: highScoreMap.get(ownerId)?.get(r.season) ?? 0,
          result,
          finish,
        };
      })
      .sort((a, b) => a.year.localeCompare(b.year));

    const rivalries: RivalryEntry[] = [
      ...(rivalryMap.get(ownerId) ?? new Map<string, RivalryAcc>()).entries(),
    ]
      .filter(([oppId]) => ownerUsernames.has(oppId))
      .map(([oppId, data]) => ({
        oppId,
        oppName: ownerUsernames.get(oppId)!,
        oppTeam: ownerCurrentTeams.get(oppId) ?? '',
        oppColor: colorMap.get(oppId) ?? avatarColor(0),
        oppInit: managerInitials(ownerUsernames.get(oppId)!),
        w: data.w,
        l: data.l,
        avgFor: data.count > 0 ? data.totalFor / data.count : 0,
        avgAgainst: data.count > 0 ? data.totalAgainst / data.count : 0,
        lastResult: data.lastWon ? ('W' as const) : ('L' as const),
      }));

    return {
      owner_id: ownerId,
      owner_username: mostRecent.owner_username,
      init: managerInitials(mostRecent.owner_username),
      color: colorMap.get(ownerId) ?? avatarColor(colorIdx),
      currentTeam: mostRecent.team_name,
      allTime: {
        wins: allWins,
        losses: allLosses,
        championships,
        playoffs,
        highScore: Math.round(allTimeHigh * 100) / 100,
        avgPts: Math.round(avgPts * 100) / 100,
      },
      seasons,
      rivalries,
    };
  });
}

// ── Skeleton ──────────────────────────────────────────────────────────────────

function SkeletonManagerHistory() {
  return (
    <div>
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <Skeleton className="w-14 h-14 rounded-full shrink-0" />
        <div className="flex-1 flex flex-col gap-1.5">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-3 w-24" />
        </div>
        <Skeleton className="h-9 w-36 rounded-md" />
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-5 gap-2.5 mb-6">
        {Array.from({ length: 5 }).map((_, i) => (
          <div
            key={i}
            className="bg-card border border-border/50 rounded-lg p-3"
          >
            <Skeleton className="h-2.5 w-20 mb-2" />
            <Skeleton className="h-6 w-14 mb-1" />
            <Skeleton className="h-2.5 w-16" />
          </div>
        ))}
      </div>

      {/* Season finish chart */}
      <Skeleton className="h-3 w-28 mb-2.5" />
      <div className="bg-card border border-border/50 rounded-lg p-5 mb-6">
        <Skeleton className="w-full h-48" />
      </div>

      {/* Season cards */}
      <Skeleton className="h-3 w-36 mb-2.5" />
      <div className="flex flex-col gap-2.5 mb-6">
        {Array.from({ length: 3 }).map((_, i) => (
          <div
            key={i}
            className="bg-card border border-border/50 rounded-lg p-3.5 grid grid-cols-[80px_1fr_auto] gap-3 items-center"
          >
            <div className="flex flex-col gap-1.5">
              <Skeleton className="h-3.5 w-14" />
              <Skeleton className="h-2.5 w-20" />
              <Skeleton className="h-5 w-16 rounded-full" />
            </div>
            <div className="flex gap-5">
              {Array.from({ length: 4 }).map((_, j) => (
                <div key={j} className="flex flex-col gap-1">
                  <Skeleton className="h-2.5 w-10" />
                  <Skeleton className="h-3.5 w-12" />
                </div>
              ))}
            </div>
            <div className="flex flex-col items-end gap-1">
              <Skeleton className="h-6 w-10" />
              <Skeleton className="h-2.5 w-8" />
            </div>
          </div>
        ))}
      </div>

      {/* Rivalry cards */}
      <Skeleton className="h-3 w-16 mb-2.5" />
      <div className="grid grid-cols-3 gap-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <div
            key={i}
            className="bg-card border border-border/50 rounded-lg p-3.5 flex flex-col gap-2.5"
          >
            <div className="flex items-center gap-2.5">
              <Skeleton className="w-9 h-9 rounded-full shrink-0" />
              <div className="flex-1 flex flex-col gap-1">
                <Skeleton className="h-3 w-20" />
                <Skeleton className="h-2.5 w-16" />
              </div>
              <Skeleton className="h-5 w-16 rounded-full" />
            </div>
            <div className="flex flex-col gap-1.5">
              <Skeleton className="h-5 w-16" />
              <Skeleton className="h-1.5 w-full rounded-full" />
            </div>
            <div className="flex gap-4">
              {Array.from({ length: 4 }).map((_, j) => (
                <div key={j} className="flex flex-col gap-0.5">
                  <Skeleton className="h-2.5 w-10" />
                  <Skeleton className="h-3 w-10" />
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Content ───────────────────────────────────────────────────────────────────

function ManagerHistoryContent({ promise }: { promise: Promise<DataResult> }) {
  const result = use(promise);
  const [selectedManagerIndex, setSelectedManagerIndex] = useState(0);

  if (!result.ok) {
    return (
      <div className="text-center py-8 text-[13px] text-destructive">
        {result.error}
      </div>
    );
  }

  const managers = result.data;
  if (managers.length === 0) {
    return (
      <div className="text-center py-8 text-[13px] text-muted-foreground">
        No manager data available.
      </div>
    );
  }

  const idx = Math.min(selectedManagerIndex, managers.length - 1);
  const m = managers[idx];
  const at = m.allTime;

  const finishValues = m.seasons
    .filter((s) => s.finish !== null)
    .map((s) => s.finish!);
  const maxFinish = finishValues.length > 0 ? Math.max(...finishValues) : 12;
  const rankChartData = m.seasons.map((s) => ({ year: s.year, finish: s.finish }));
  const rankChartConfig: ChartConfig = { finish: { label: 'Finish', color: m.color } };

  const winPct =
    at.wins + at.losses > 0
      ? (at.wins / (at.wins + at.losses)).toFixed(3)
      : '0.000';

  const sorted = [...m.rivalries].sort((a, b) => {
    const aRate = a.w + a.l > 0 ? a.w / (a.w + a.l) : 0;
    const bRate = b.w + b.l > 0 ? b.w / (b.w + b.l) : 0;
    return bRate - aRate;
  });
  const best = sorted
    .filter((r) => r.w + r.l > 0 && r.w / (r.w + r.l) >= 0.65)
    .slice(0, 2);
  const worst = [...sorted]
    .reverse()
    .filter((r) => r.w + r.l > 0 && r.w / (r.w + r.l) < 0.4)
    .slice(0, 2);
  const closest = [...m.rivalries]
    .sort((a, b) => {
      const aDiff = Math.abs(a.avgFor - a.avgAgainst);
      const bDiff = Math.abs(b.avgFor - b.avgAgainst);
      return aDiff - bDiff;
    })
    .slice(0, 2);

  return (
    <div>
      {/* Manager header */}
      <div className="flex items-center gap-4 mb-6">
        <div
          className="w-14 h-14 rounded-full flex items-center justify-center text-[18px] font-medium text-white shrink-0"
          style={{ background: m.color }}
        >
          {m.init}
        </div>
        <div className="flex-1">
          <div className="text-[18px] font-medium text-foreground mb-0.5">
            {m.owner_username}
          </div>
          <div className="text-[13px] text-muted-foreground">
            {m.currentTeam}
          </div>
        </div>
        {managers.length > 1 && (
          <select
            className="px-3 py-2 text-[13px] font-medium bg-card border border-border rounded-md text-foreground cursor-pointer"
            value={idx}
            onChange={(e) => setSelectedManagerIndex(Number(e.target.value))}
          >
            {managers.map((mgr, i) => (
              <option key={mgr.owner_id} value={i}>
                {mgr.owner_username}
              </option>
            ))}
          </select>
        )}
      </div>

      {/* All-time stat cards */}
      <div className="grid grid-cols-5 gap-2.5 mb-6">
        <div className="bg-card border border-border/50 rounded-lg p-3">
          <div className="text-[11px] font-medium uppercase tracking-[0.06em] text-muted-foreground mb-1">
            All-time record
          </div>
          <div className="text-[22px] font-medium text-foreground">
            {at.wins}-{at.losses}
          </div>
          <div className="text-[11px] text-muted-foreground mt-0.5">
            {winPct} win percentage
          </div>
        </div>
        <div className="bg-card border border-border/50 rounded-lg p-3">
          <div className="text-[11px] font-medium uppercase tracking-[0.06em] text-muted-foreground mb-1">
            Championships
          </div>
          <div className="text-[22px] font-medium text-foreground">
            {at.championships}
          </div>
          <div className="text-[11px] text-muted-foreground mt-0.5">
            of {m.seasons.length} seasons
          </div>
        </div>
        <div className="bg-card border border-border/50 rounded-lg p-3">
          <div className="text-[11px] font-medium uppercase tracking-[0.06em] text-muted-foreground mb-1">
            Playoff apps
          </div>
          <div className="text-[22px] font-medium text-foreground">
            {at.playoffs}
          </div>
          <div className="text-[11px] text-muted-foreground mt-0.5">
            of {m.seasons.length} seasons
          </div>
        </div>
        <div className="bg-card border border-border/50 rounded-lg p-3">
          <div className="text-[11px] font-medium uppercase tracking-[0.06em] text-muted-foreground mb-1">
            Avg pts / wk
          </div>
          <div className="text-[22px] font-medium text-foreground">
            {at.avgPts.toFixed(1)}
          </div>
          <div className="text-[11px] text-muted-foreground mt-0.5">
            all-time
          </div>
        </div>
        <div className="bg-card border border-border/50 rounded-lg p-3">
          <div className="text-[11px] font-medium uppercase tracking-[0.06em] text-muted-foreground mb-1">
            High score
          </div>
          <div className="text-[22px] font-medium text-foreground">
            {at.highScore.toFixed(2)}
          </div>
          <div className="text-[11px] text-muted-foreground mt-0.5">
            single week
          </div>
        </div>
      </div>

      {/* Season finish chart */}
      <p className="text-[11px] font-medium uppercase tracking-[0.08em] text-muted-foreground mb-2.5">
        Season finish
      </p>
      <div className="bg-card border border-border/50 rounded-lg p-5 mb-6">
        {finishValues.length > 0 ? (
          <ChartContainer
            config={rankChartConfig}
            className="h-48 w-full aspect-auto"
          >
            <LineChart
              data={rankChartData}
              margin={{ top: 4, right: 4, left: 0, bottom: 4 }}
            >
              <CartesianGrid vertical={false} />
              <XAxis
                dataKey="year"
                tickLine={false}
                axisLine={false}
                tickMargin={8}
              />
              <YAxis
                reversed
                allowDecimals={false}
                domain={[1, maxFinish]}
                tickFormatter={(v: number) => ordinal(v)}
                tickLine={false}
                axisLine={false}
                width={36}
              />
              <ChartTooltip
                content={({ active, payload, label }) => {
                  if (!active || !payload?.length) return null;
                  const finish = payload[0]?.value;
                  return (
                    <div className="grid min-w-32 items-start gap-1.5 rounded-lg border border-border/50 bg-background px-2.5 py-1.5 text-xs shadow-xl">
                      <p className="font-medium">{String(label)} Season</p>
                      <div className="flex items-center gap-2">
                        <div
                          className="h-2 w-2 shrink-0 rounded-xs"
                          style={{ backgroundColor: m.color }}
                        />
                        <span className="text-muted-foreground">Finish</span>
                        <span className="font-mono font-medium text-foreground tabular-nums ml-auto">
                          {finish != null ? ordinal(Number(finish)) : '—'}
                        </span>
                      </div>
                    </div>
                  );
                }}
              />
              <Line
                type="monotone"
                dataKey="finish"
                stroke={`var(--color-finish)`}
                strokeWidth={2}
                dot={{ r: 4, fill: `var(--color-finish)`, strokeWidth: 0 }}
                activeDot={{ r: 5 }}
                connectNulls={false}
              />
            </LineChart>
          </ChartContainer>
        ) : (
          <p className="text-[13px] text-muted-foreground text-center py-4">
            No finish data available.
          </p>
        )}
      </div>

      {/* Season-by-season */}
      <p className="text-[11px] font-medium uppercase tracking-[0.08em] text-muted-foreground mb-2.5">
        Season-by-season results
      </p>
      <div className="flex flex-col gap-2.5 mb-6">
        {[...m.seasons].reverse().map((s) => (
          <div
            key={s.year}
            className={`bg-card border border-border/50 rounded-lg p-3.5 grid grid-cols-[80px_1fr_auto] gap-3 items-center ${
              s.result === 'champion' ? 'border-2' : ''
            }`}
            style={s.result === 'champion' ? { borderColor: '#534AB7' } : {}}
          >
            <div>
              <div className="text-[13px] font-medium text-foreground">
                {s.year}
              </div>
              <div className="text-[11px] text-muted-foreground mt-0.5">
                {s.team || ' '}
              </div>
              <div className="mt-2">{resultBadge(s.result)}</div>
            </div>
            <div className="flex gap-5 flex-wrap">
              <div>
                <div className="text-[10px] font-medium uppercase tracking-[0.06em] text-muted-foreground">
                  Record
                </div>
                <div className="text-[14px] font-medium text-foreground">
                  {s.record}
                </div>
              </div>
              <div>
                <div className="text-[10px] font-medium uppercase tracking-[0.06em] text-muted-foreground">
                  Total pts
                </div>
                <div className="text-[14px] font-medium text-foreground">
                  {s.pts.toLocaleString(undefined, {
                    maximumFractionDigits: 2,
                  })}
                </div>
              </div>
              <div>
                <div className="text-[10px] font-medium uppercase tracking-[0.06em] text-muted-foreground">
                  Avg / wk
                </div>
                <div className="text-[14px] font-medium text-foreground">
                  {s.avg.toFixed(1)}
                </div>
              </div>
              <div>
                <div className="text-[10px] font-medium uppercase tracking-[0.06em] text-muted-foreground">
                  High score
                </div>
                <div className="text-[14px] font-medium text-foreground">
                  {s.high.toFixed(2)}
                </div>
              </div>
            </div>
            <div className="flex flex-col items-end gap-1.5">
              <div className="text-[20px] font-medium text-foreground">
                {s.finish != null ? ordinal(s.finish) : '—'}
              </div>
              <div className="text-[11px] text-muted-foreground">place</div>
            </div>
          </div>
        ))}
      </div>

      {/* Rivalries */}
      {m.rivalries.length >= 3 && (
        <>
          <div className="flex items-center gap-1.5 mb-2.5">
            <p className="text-[11px] font-medium uppercase tracking-[0.08em] text-muted-foreground">
              Rivalries
            </p>
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Info className="w-3 h-3 text-muted-foreground cursor-default" />
                </TooltipTrigger>
                <TooltipContent
                  side="right"
                  className="max-w-56 leading-relaxed bg-popover text-popover-foreground border border-border shadow-md [&>svg]:fill-popover [&>svg]:bg-popover"
                >
                  <p className="text-[12px]">
                    <span className="font-semibold">Domination</span> win
                    pct ≥ 0.650
                  </p>
                  <p className="text-[12px] mt-1">
                    <span className="font-semibold">Nemesis</span> win
                    pct &lt; 0.400
                  </p>
                  <p className="text-[12px] mt-1">
                    <span className="font-semibold">Rival</span> lowest
                    margin
                  </p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
          <div className="grid grid-cols-3 gap-3 mb-6">
            {[
              ...best.map((r) => ({ r, type: 'best' as const })),
              ...worst.map((r) => ({ r, type: 'worst' as const })),
              ...(closest[0]
                ? [{ r: closest[0], type: 'closest' as const }]
                : []),
            ].map(({ r, type }) => {
              const total = r.w + r.l;
              const winRate = total > 0 ? (r.w / total).toFixed(3) : '0.000';
              const fillPct = pct(r.w, r.l);
              let typeBadge, typeColor;
              if (type === 'best') {
                typeBadge = (
                  <span
                    className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-medium"
                    style={{ background: '#E1F5EE', color: '#085041' }}
                  >
                    Domination
                  </span>
                );
                typeColor = '#0F6E56';
              } else if (type === 'worst') {
                typeBadge = (
                  <span
                    className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-medium"
                    style={{ background: '#FCEBEB', color: '#791F1F' }}
                  >
                    Nemesis
                  </span>
                );
                typeColor = '#E24B4A';
              } else {
                typeBadge = (
                  <span
                    className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-medium"
                    style={{ background: '#FAEEDA', color: '#633806' }}
                  >
                    Rival
                  </span>
                );
                typeColor = '#BA7517';
              }
              const margin = (r.avgFor - r.avgAgainst).toFixed(1);
              const marginSign = parseFloat(margin) > 0 ? '+' : '';
              return (
                <div
                  key={r.oppId}
                  className="bg-card border border-border/50 rounded-lg p-3.5 flex flex-col gap-2.5"
                >
                  <div className="flex items-center gap-2.5">
                    <div
                      className="w-9 h-9 rounded-full flex items-center justify-center text-[12px] font-medium text-white shrink-0"
                      style={{ background: r.oppColor }}
                    >
                      {r.oppInit}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-[13px] font-medium text-foreground">
                        {r.oppName}
                      </div>
                      <div className="text-[11px] text-muted-foreground">
                        {r.oppTeam}
                      </div>
                    </div>
                    <div className="shrink-0">{typeBadge}</div>
                  </div>
                  <div>
                    <div className="flex items-baseline gap-1.5 mb-1.5">
                      <span
                        className="text-[18px] font-medium"
                        style={{ color: typeColor }}
                      >
                        {r.w}-{r.l}
                      </span>
                      <span className="text-[11px] text-muted-foreground">
                        {winRate} win percentage
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="h-1.5 rounded-full bg-muted overflow-hidden flex-1">
                        <div
                          className="h-full rounded-full"
                          style={{
                            width: `${fillPct}%`,
                            background: typeColor,
                          }}
                        />
                      </div>
                      <span className="text-[11px] text-muted-foreground whitespace-nowrap">
                        {total} games
                      </span>
                    </div>
                  </div>
                  <div className="flex gap-4">
                    <div className="flex flex-col gap-0.5">
                      <div className="text-[10px] font-medium uppercase tracking-[0.06em] text-muted-foreground">
                        Avg for
                      </div>
                      <div className="text-[13px] font-medium text-foreground">
                        {r.avgFor.toFixed(1)}
                      </div>
                    </div>
                    <div className="flex flex-col gap-0.5">
                      <div className="text-[10px] font-medium uppercase tracking-[0.06em] text-muted-foreground">
                        Avg against
                      </div>
                      <div className="text-[13px] font-medium text-foreground">
                        {r.avgAgainst.toFixed(1)}
                      </div>
                    </div>
                    <div className="flex flex-col gap-0.5">
                      <div className="text-[10px] font-medium uppercase tracking-[0.06em] text-muted-foreground">
                        Avg margin
                      </div>
                      <div
                        className="text-[13px] font-medium"
                        style={{
                          color:
                            parseFloat(margin) >= 0 ? '#27500A' : '#791F1F',
                        }}
                      >
                        {marginSign}
                        {margin}
                      </div>
                    </div>
                    <div className="flex flex-col gap-0.5">
                      <div className="text-[10px] font-medium uppercase tracking-[0.06em] text-muted-foreground">
                        Last game
                      </div>
                      <div
                        className="text-[13px] font-medium"
                        style={{
                          color: r.lastResult === 'W' ? '#27500A' : '#791F1F',
                        }}
                      >
                        {r.lastResult}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function ManagerHistory() {
  const leagueId = getCookie('leagueId');
  const platform = (getCookie('leaguePlatform') || 'ESPN') as
    | 'ESPN'
    | 'SLEEPER';

  const seasons = useMemo(() => {
    try {
      return JSON.parse(
        decodeURIComponent(getCookie('leagueSeasons')),
      ) as string[];
    } catch {
      return [];
    }
  }, []);

  const dataPromise = useMemo(
    (): Promise<DataResult> =>
      leagueId && seasons.length > 0
        ? getManagerHistoryData(leagueId, platform, seasons)
            .then(({ standings, matchups }) => ({
              ok: true as const,
              data: processData(standings, matchups),
            }))
            .catch((err: unknown) => ({
              ok: false as const,
              error:
                err instanceof Error
                  ? err.message
                  : 'Failed to load manager data.',
            }))
        : Promise.resolve({ ok: true as const, data: [] }),
    [leagueId, platform, seasons],
  );

  return (
    <div className="flex flex-1 flex-col p-6 overflow-auto">
      <div className="max-w-225 mx-auto w-full">
        <Suspense fallback={<SkeletonManagerHistory />}>
          <ManagerHistoryContent promise={dataPromise} />
        </Suspense>
      </div>
    </div>
  );
}
