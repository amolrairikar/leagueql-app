import { Clover, Info } from 'lucide-react';
import { Suspense, use, useMemo, useState } from 'react';
import { CartesianGrid, Line, LineChart, XAxis, YAxis } from 'recharts';

import { avatarColor, TeamAvatar } from '@/components/team-avatar';
import {
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
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
  type WeeklyStandingItem,
  getSeasonWeeklyStandings,
} from '@/features/matchups/api-calls';
import { getLeagueCookies } from '@/lib/cookie-handler';
import { POSITION_COLORS, UI_COLORS } from '@/lib/color-constants';
import SeasonSelect from '@/features/season_select/season-select';
import {
  type SeasonStandingsItem,
  getSeasonStandings,
} from '@/features/season_standings/api-calls';

type StandingsResult =
  | { ok: true; data: SeasonStandingsItem[] }
  | { ok: false; error: string };

type WeeklyResult =
  | { ok: true; data: WeeklyStandingItem[] }
  | { ok: false; error: string };

function SkeletonChart() {
  return <Skeleton className="w-full h-80" />;
}

function WinsProgressionChart({ promise }: { promise: Promise<WeeklyResult> }) {
  const result = use(promise);

  if (!result.ok || result.data.length === 0) {
    return (
      <p className="text-[13px] text-muted-foreground text-center py-8">
        {result.ok ? 'No data available for this season.' : result.error}
      </p>
    );
  }

  const weekly = result.data;

  const maxWeek = Math.max(...weekly.map((d) => Number(d.snapshot_week)));
  const finalWeek = weekly.filter((d) => Number(d.snapshot_week) === maxWeek);
  const teams = [...finalWeek]
    .sort((a, b) => b.wins - a.wins || a.owner_username.localeCompare(b.owner_username))
    .map((d) => ({ team_id: d.team_id, owner_username: d.owner_username }));

  const weeks = [...new Set(weekly.map((d) => Number(d.snapshot_week)))].sort(
    (a, b) => a - b,
  );

  const chartData = weeks.map((week) => {
    const point: Record<string, number | string> = { week };
    for (const entry of weekly.filter((d) => Number(d.snapshot_week) === week)) {
      point[entry.team_id] = entry.wins;
    }
    return point;
  });

  const chartConfig: ChartConfig = Object.fromEntries(
    teams.map((team, i) => [
      team.team_id,
      { label: team.owner_username, color: avatarColor(i) },
    ]),
  );

  return (
    <ChartContainer config={chartConfig} className="h-80 w-full aspect-auto">
      <LineChart data={chartData} margin={{ top: 4, right: 4, left: 0, bottom: 4 }}>
        <CartesianGrid vertical={false} />
        <XAxis
          dataKey="week"
          tickFormatter={(v: number) => `Wk ${v}`}
          tickLine={false}
          axisLine={false}
          tickMargin={8}
        />
        <YAxis allowDecimals={false} tickLine={false} axisLine={false} width={28} />
        <ChartTooltip
          content={
            <ChartTooltipContent
              labelFormatter={(label) => `Week ${String(label)}`}
              indicator="line"
            />
          }
        />
        <ChartLegend content={<ChartLegendContent className="flex-wrap" />} />
        {teams.map((team) => (
          <Line
            key={team.team_id}
            type="monotone"
            dataKey={team.team_id}
            stroke={`var(--color-${team.team_id})`}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
          />
        ))}
      </LineChart>
    </ChartContainer>
  );
}

function StandingsBody({ promise }: { promise: Promise<StandingsResult> }) {
  const result = use(promise);

  if (!result.ok) {
    return (
      <tbody>
        <tr>
          <td
            colSpan={6}
            className="px-3.5 py-4 text-center text-[13px] text-destructive"
          >
            {result.error}
          </td>
        </tr>
      </tbody>
    );
  }

  const { data: standings } = result;

  return (
    <tbody>
      {standings.map((row, i) => {
        return (
          <tr
            key={row.team_id}
            className="border-b border-border/50 last:border-0 bg-card"
          >
            <td className="px-3.5 py-2.5 sticky left-0 z-10 bg-card">
              <div className="flex items-center gap-2">
                <span className="text-[12px] text-muted-foreground w-4 text-right shrink-0">
                  {i + 1}
                </span>
                <TeamAvatar
                  teamLogo={row.team_logo}
                  teamName={row.team_name}
                  ownerUsername={row.owner_username}
                  color={avatarColor(i)}
                />
                <div className="flex flex-col">
                  <span className="text-[13px] font-medium text-foreground">
                    {row.owner_username}
                  </span>
                  <span className="text-[11px] text-muted-foreground">
                    {row.team_name}
                  </span>
                </div>
              </div>
            </td>
            <td className="px-3.5 py-2.5 text-right text-muted-foreground">
              {row.record}
            </td>
            <td className="px-3.5 py-2.5 text-right text-muted-foreground">
              {row.avg_pf.toFixed(1)}
            </td>
            <td className="px-3.5 py-2.5 text-right text-muted-foreground">
              {row.avg_pa.toFixed(1)}
            </td>
            <td className="px-3.5 py-2.5 text-right text-muted-foreground">
              {row.win_pct.toFixed(3)}
            </td>
            <td className="px-3.5 py-2.5 text-right text-muted-foreground">
              {row.win_pct_vs_league.toFixed(3)}
            </td>
          </tr>
        );
      })}
    </tbody>
  );
}

function AwardsGrid({ promise }: { promise: Promise<StandingsResult> }) {
  const result = use(promise);
  if (!result.ok || result.data.length === 0) return null;

  const standings = result.data;

  const champion = standings.find((s) => s.champion === 'Yes') ?? null;
  const highScorer = standings.reduce((a, b) => (a.avg_pf > b.avg_pf ? a : b));
  const luckiest = standings.reduce((a, b) =>
    a.win_pct - a.win_pct_vs_league > b.win_pct - b.win_pct_vs_league ? a : b,
  );
  const luckDiff = luckiest.win_pct - luckiest.win_pct_vs_league;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-6">
      {/* Season Champion */}
      <div className="bg-card border border-border/50 rounded-lg p-4 flex flex-col gap-2.5">
        <div className="flex items-center gap-2.5">
          <div
            className="w-9 h-9 rounded-md flex items-center justify-center shrink-0"
            style={{ background: UI_COLORS.champion.bg }}
          >
            <svg
              className="w-4.5 h-4.5"
              viewBox="0 0 24 24"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                d="M12 2v14M8 20h8M6 2h12v8a6 6 0 01-12 0V2z"
                stroke={UI_COLORS.champion.border}
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <path
                d="M6 6H3a2 2 0 002 2h1M18 6h3a2 2 0 01-2 2h-1"
                stroke={UI_COLORS.champion.border}
                strokeWidth="1.5"
                strokeLinecap="round"
              />
            </svg>
          </div>
          <span
            className="text-[11px] font-medium uppercase tracking-[0.07em]"
            style={{ color: UI_COLORS.champion.border }}
          >
            Season Champion
          </span>
        </div>
        <div>
          {champion ? (
            <>
              <div className="text-[15px] font-medium text-foreground">
                {champion.owner_username}
              </div>
              <div className="text-[12px] text-muted-foreground">
                {champion.team_name}
              </div>
              <div
                className="text-[11px] font-medium mt-0.5"
                style={{ color: UI_COLORS.champion.border }}
              >
                {champion.record} · {champion.win_pct.toFixed(3)} Win%
              </div>
            </>
          ) : (
            <>
              <div className="text-[15px] font-medium text-foreground">
                TBD
              </div>
              <div className="text-[12px] text-muted-foreground">
                Season in progress
              </div>
            </>
          )}
        </div>
      </div>

      {/* High Scorer */}
      <div className="bg-card border border-border/50 rounded-lg p-4 flex flex-col gap-2.5">
        <div className="flex items-center gap-2.5">
          <div
            className="w-9 h-9 rounded-md flex items-center justify-center shrink-0"
            style={{ background: POSITION_COLORS.TE.bg }}
          >
            <svg
              className="w-4.5 h-4.5"
              viewBox="0 0 24 24"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"
                stroke={POSITION_COLORS.TE.color}
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
          <span
            className="text-[11px] font-medium uppercase tracking-[0.07em]"
            style={{ color: POSITION_COLORS.TE.color }}
          >
            High Scorer
          </span>
        </div>
        <div>
          <div className="text-[15px] font-medium text-foreground">
            {highScorer.owner_username}
          </div>
          <div className="text-[12px] text-muted-foreground">
            {highScorer.team_name}
          </div>
          <div
            className="text-[11px] font-medium mt-0.5"
            style={{ color: POSITION_COLORS.TE.color }}
          >
            {highScorer.avg_pf.toFixed(1)} PF/Game
          </div>
        </div>
      </div>

      {/* Luckiest Team */}
      <div className="bg-card border border-border/50 rounded-lg p-4 flex flex-col gap-2.5">
        <div className="flex items-center gap-2.5">
          <div
            className="w-9 h-9 rounded-md flex items-center justify-center shrink-0"
            style={{ background: POSITION_COLORS.RB.bg }}
          >
            <Clover size={18} stroke={POSITION_COLORS.RB.color} strokeWidth={1.5} />
          </div>
          <span
            className="text-[11px] font-medium uppercase tracking-[0.07em]"
            style={{ color: POSITION_COLORS.RB.color }}
          >
            Luckiest Team
          </span>
        </div>
        <div>
          <div className="text-[15px] font-medium text-foreground">
            {luckiest.owner_username}
          </div>
          <div className="text-[12px] text-muted-foreground">
            {luckiest.team_name}
          </div>
          <div
            className="text-[11px] font-medium mt-0.5"
            style={{ color: POSITION_COLORS.RB.color }}
          >
            {luckDiff >= 0 ? '+' : ''}
            {luckDiff.toFixed(3)} vs. expected Win%
          </div>
        </div>
      </div>
    </div>
  );
}

function SkeletonAwards() {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-6">
      {Array.from({ length: 3 }).map((_, i) => (
        <div
          key={i}
          className="bg-card border border-border/50 rounded-lg p-4 flex flex-col gap-2.5"
        >
          <div className="flex items-center gap-2.5">
            <Skeleton className="w-9 h-9 rounded-md shrink-0" />
            <Skeleton className="h-3 w-24" />
          </div>
          <div className="flex flex-col gap-1.5">
            <Skeleton className="h-4 w-28" />
            <Skeleton className="h-3 w-20" />
            <Skeleton className="h-3 w-24" />
          </div>
        </div>
      ))}
    </div>
  );
}

function SkeletonBody() {
  return (
    <tbody>
      {Array.from({ length: 8 }).map((_, i) => (
        <tr key={i} className="border-b border-border/50">
          <td className="px-3.5 py-2.5 sticky left-0 z-10 bg-card">
            <div className="flex items-center gap-2">
              <Skeleton className="w-4 h-3 shrink-0" />
              <Skeleton className="w-7 h-7 rounded-full shrink-0" />
              <Skeleton className="h-3 w-28" />
            </div>
          </td>
          {Array.from({ length: 5 }).map((_, j) => (
            <td key={j} className="px-3.5 py-2.5 text-right">
              <Skeleton className="h-3 w-12 ml-auto" />
            </td>
          ))}
        </tr>
      ))}
    </tbody>
  );
}

export default function SeasonStandings() {
  const { leagueId, platform, seasons } = useMemo(() => getLeagueCookies(), []);

  const defaultSeason =
    [...seasons].sort((a, b) => Number(b) - Number(a))[0] ?? '';
  const [selectedSeason, setSelectedSeason] = useState(defaultSeason);

  const standingsPromise = useMemo(
    (): Promise<StandingsResult> =>
      leagueId && selectedSeason
        ? getSeasonStandings(leagueId, platform, selectedSeason)
            .then((res) => ({ ok: true as const, data: res.data }))
            .catch((err: unknown) => ({
              ok: false as const,
              error:
                err instanceof Error
                  ? err.message
                  : 'Failed to load standings.',
            }))
        : Promise.resolve({ ok: true as const, data: [] }),
    [leagueId, platform, selectedSeason],
  );

  const weeklyStandingsPromise = useMemo(
    (): Promise<WeeklyResult> =>
      leagueId && selectedSeason
        ? getSeasonWeeklyStandings(leagueId, platform, selectedSeason)
            .then((res) => ({ ok: true as const, data: res.data }))
            .catch((err: unknown) => ({
              ok: false as const,
              error:
                err instanceof Error
                  ? err.message
                  : 'Failed to load weekly standings.',
            }))
        : Promise.resolve({ ok: true as const, data: [] }),
    [leagueId, platform, selectedSeason],
  );

  return (
    <div className="flex flex-1 flex-col p-6 overflow-auto">
      <div className="max-w-225 mx-auto w-full">
        {seasons.length > 0 && (
          <div className="mb-4">
            <SeasonSelect
              seasons={seasons}
              value={selectedSeason}
              onValueChange={setSelectedSeason}
            />
          </div>
        )}

        <p className="text-[11px] font-medium uppercase tracking-[0.08em] text-muted-foreground mb-2.5">
          Season awards
        </p>

        <Suspense fallback={<SkeletonAwards />}>
          <AwardsGrid promise={standingsPromise} />
        </Suspense>

        <p className="text-[11px] font-medium uppercase tracking-[0.08em] text-muted-foreground mb-2.5">
          Season standings
        </p>

        <div className="bg-card border border-border/50 rounded-lg overflow-hidden mb-6">
          <div className="overflow-x-auto">
            <table
              className="w-full border-collapse text-[13px]"
              style={{ tableLayout: 'fixed', minWidth: '540px' }}
            >
              <thead>
                <tr>
                  <th
                    className="text-left text-[10px] font-medium uppercase tracking-[0.07em] text-muted-foreground px-3.5 py-2.5 border-b border-border/50 bg-muted sticky left-0 z-10"
                    style={{ width: '48%' }}
                  >
                    Owner
                  </th>
                  <th
                    className="text-right text-[10px] font-medium uppercase tracking-[0.07em] text-muted-foreground px-3.5 py-2.5 border-b border-border/50 bg-muted"
                    style={{ width: '15%' }}
                  >
                    Record
                  </th>
                  <th
                    className="text-right text-[10px] font-medium uppercase tracking-[0.07em] text-muted-foreground px-3.5 py-2.5 border-b border-border/50 bg-muted"
                    style={{ width: '12%' }}
                  >
                    PF/Game
                  </th>
                  <th
                    className="text-right text-[10px] font-medium uppercase tracking-[0.07em] text-muted-foreground px-3.5 py-2.5 border-b border-border/50 bg-muted"
                    style={{ width: '12%' }}
                  >
                    PA/Game
                  </th>
                  <th
                    className="text-right text-[10px] font-medium uppercase tracking-[0.07em] text-muted-foreground px-3.5 py-2.5 border-b border-border/50 bg-muted"
                    style={{ width: '14%' }}
                  >
                    Win %
                  </th>
                  <th
                    className="text-right text-[10px] font-medium uppercase tracking-[0.07em] text-muted-foreground px-3.5 py-2.5 border-b border-border/50 bg-muted"
                    style={{ width: '14%' }}
                  >
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <span className="inline-flex items-center justify-end gap-1 cursor-default">
                            Win % vs. League
                            <Info className="w-3 h-3 shrink-0" />
                          </span>
                        </TooltipTrigger>
                        <TooltipContent
                          side="top"
                          className="max-w-64 text-center leading-relaxed bg-popover text-popover-foreground border border-border shadow-md [&>svg]:fill-popover [&>svg]:bg-popover"
                        >
                          This percentage measures a team&apos;s win percentage
                          if they played every team in the league each week
                          aggregated over the season (i.e., if a team was the
                          2nd highest scoring team in a 10 team league, their
                          win % vs. league for that week would be .900)
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  </th>
                </tr>
              </thead>
              <Suspense fallback={<SkeletonBody />}>
                <StandingsBody promise={standingsPromise} />
              </Suspense>
            </table>
          </div>
        </div>

        <p className="text-[11px] font-medium uppercase tracking-[0.08em] text-muted-foreground mb-2.5">
          Wins progression
        </p>
        <div className="bg-card border border-border/50 rounded-lg p-5">
          <Suspense fallback={<SkeletonChart />}>
            <WinsProgressionChart promise={weeklyStandingsPromise} />
          </Suspense>
        </div>
      </div>
    </div>
  );
}
