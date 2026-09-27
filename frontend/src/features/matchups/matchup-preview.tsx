import { X } from 'lucide-react';
import { type ReactNode, useMemo } from 'react';
import {
  Area,
  AreaChart,
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  XAxis,
  YAxis,
} from 'recharts';

import { TeamAvatar } from '@/components/team-avatar';
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from '@/components/ui/chart';
import type {
  MatchupPreviewData,
  TeamPreviewStats,
} from '@/features/matchups/compute-preview';
import { positionColorMeta } from '@/lib/color-constants';
import { pct } from '@/lib/utils';

/** Display fields for one side of the preview (colors/names/logo). */
export interface PreviewSide {
  teamId: string;
  teamName: string;
  ownerUsername: string;
  teamLogo: string | null;
  color: string;
}

const pctLabel = (v: number): string => `${Math.round(v * 100)}%`;
const one = (v: number): string => v.toFixed(1);
/** Win fraction as a 3-decimal average, no leading zero (e.g. `.857`). */
const avg3 = (v: number): string => v.toFixed(3).replace(/^0/, '');

function StatComparison({
  a,
  b,
  colorA,
  colorB,
}: {
  a: TeamPreviewStats;
  b: TeamPreviewStats;
  colorA: string;
  colorB: string;
}) {
  // Consistency (σ) is only meaningful once each team has enough games for its
  // own standard deviation (see the MIN_GAMES_FOR_OWN_STD threshold in
  // buildTeamScoring). Before that both teams share the identical league-wide
  // fallback σ, so the row is hidden until the two values actually differ per
  // team (roughly after week 3).
  const stdA = a.scoring?.std ?? null;
  const stdB = b.scoring?.std ?? null;
  const showConsistency = stdA !== null && stdB !== null && stdA !== stdB;

  const rows: {
    label: string;
    la: number | null;
    lb: number | null;
    higherBetter: boolean;
    fmt: (v: number) => string;
  }[] = [
    {
      label: 'Win %',
      la: a.winPct,
      lb: b.winPct,
      higherBetter: true,
      fmt: avg3,
    },
    { label: 'Avg PF', la: a.avgPf, lb: b.avgPf, higherBetter: true, fmt: one },
    {
      label: 'Avg PA',
      la: a.avgPa,
      lb: b.avgPa,
      higherBetter: false,
      fmt: one,
    },
    ...(showConsistency
      ? [
          {
            label: 'Consistency (σ)',
            la: stdA,
            lb: stdB,
            higherBetter: false,
            fmt: (v: number) => `±${v.toFixed(1)}`,
          },
        ]
      : []),
    {
      label: 'Ceiling',
      la: a.highScore,
      lb: b.highScore,
      higherBetter: true,
      fmt: one,
    },
  ];

  return (
    <div className="flex flex-col gap-3.5">
      {rows.map((r) => {
        const has = r.la !== null && r.lb !== null;
        // Bar sizing uses "goodness": for lower-is-better stats a smaller value
        // should read as the fuller bar, so invert before proportioning.
        const goodness = (v: number): number =>
          r.higherBetter ? v : v > 0 ? 1 / v : 0;
        const ga = has ? goodness(r.la!) : 0;
        const gb = has ? goodness(r.lb!) : 0;
        const aWins = has && (r.higherBetter ? r.la! > r.lb! : r.la! < r.lb!);
        const bWins = has && (r.higherBetter ? r.lb! > r.la! : r.lb! < r.la!);
        const wa = has ? pct(ga, gb) : 50;
        const wb = has ? pct(gb, ga) : 50;
        return (
          <div key={r.label}>
            <div className="grid grid-cols-[1fr_96px_1fr] items-center gap-2.5">
              <span
                className={`text-right text-[13px] font-semibold tabular-nums ${aWins ? '' : 'text-muted-foreground'}`}
                style={aWins ? { color: colorA } : undefined}
              >
                {has ? r.fmt(r.la!) : '—'}
              </span>
              <span className="text-center text-[10px] font-semibold uppercase tracking-[0.05em] text-muted-foreground/70">
                {r.label}
              </span>
              <span
                className={`text-left text-[13px] font-semibold tabular-nums ${bWins ? '' : 'text-muted-foreground'}`}
                style={bWins ? { color: colorB } : undefined}
              >
                {has ? r.fmt(r.lb!) : '—'}
              </span>
            </div>
            <div className="mt-1.5 grid grid-cols-2 gap-[3px]">
              <div className="flex h-1.5 justify-end overflow-hidden rounded-full bg-muted">
                <div
                  className="h-full rounded-full"
                  style={{
                    width: `${wa}%`,
                    background: aWins ? colorA : 'var(--color-border)',
                  }}
                />
              </div>
              <div className="flex h-1.5 overflow-hidden rounded-full bg-muted">
                <div
                  className="h-full rounded-full"
                  style={{
                    width: `${wb}%`,
                    background: bWins ? colorB : 'var(--color-border)',
                  }}
                />
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function streakLabel(form: TeamPreviewStats['recentForm']): string {
  if (form.length === 0) return 'No games yet';
  const last = form[form.length - 1].result;
  let n = 0;
  for (let i = form.length - 1; i >= 0; i--) {
    if (form[i].result === last) n++;
    else break;
  }
  const verb = last === 'W' ? 'Won' : last === 'L' ? 'Lost' : 'Tied';
  return n === 1 ? `${verb} last game` : `${verb} ${n} in a row`;
}

function RecentForm({
  side,
  stats,
}: {
  side: PreviewSide;
  stats: TeamPreviewStats;
}) {
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-2 text-[12px] font-semibold">
        <span
          className="h-2.5 w-2.5 rounded-full"
          style={{ background: side.color }}
        />
        {side.ownerUsername}
        <span className="ml-auto text-[11px] font-medium text-muted-foreground">
          {streakLabel(stats.recentForm)}
        </span>
      </div>
      {stats.recentForm.length === 0 ? (
        <p className="text-[12px] text-muted-foreground">
          No games played yet.
        </p>
      ) : (
        <div className="flex flex-wrap gap-1.5">
          {stats.recentForm.map((g) => (
            <div
              key={g.week}
              className="flex min-w-11 flex-col items-center gap-0.5 rounded-lg border border-border/50 bg-muted px-2 py-1.5"
            >
              <span
                className={`flex h-4.5 w-4.5 items-center justify-center rounded text-[10px] font-bold text-white ${
                  g.result === 'W'
                    ? 'bg-[#4f8a2a]'
                    : g.result === 'L'
                      ? 'bg-[#a83b3b]'
                      : 'bg-muted-foreground'
                }`}
              >
                {g.result}
              </span>
              <span className="text-[11px] font-semibold tabular-nums">
                {g.points.toFixed(1)}
              </span>
              <span className="text-[9px] text-muted-foreground/70">
                Wk{g.week}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function TopScorersColumn({
  side,
  stats,
  align,
}: {
  side: PreviewSide;
  stats: TeamPreviewStats;
  align: 'left' | 'right';
}) {
  return (
    <div
      className={
        align === 'left'
          ? 'sm:border-r sm:border-border/50 sm:pr-3.5'
          : 'sm:pl-3.5'
      }
    >
      <div className="mb-2.5 flex items-center gap-1.5">
        <TeamAvatar
          teamLogo={side.teamLogo}
          teamName={side.teamName}
          ownerUsername={side.ownerUsername}
          color={side.color}
        />
        <span className="text-[12px] font-semibold">{side.ownerUsername}</span>
      </div>
      {stats.topScorers.length === 0 ? (
        <p className="text-[12px] text-muted-foreground">No players yet.</p>
      ) : (
        <div>
          {stats.topScorers.map((p) => {
            const meta = positionColorMeta(p.position);
            return (
              <div
                key={p.playerId}
                className="flex items-center gap-2.5 border-t border-border/50 py-1.5 first:border-t-0"
              >
                <span
                  className="w-8 shrink-0 rounded py-0.5 text-center text-[10px] font-bold"
                  style={{ background: meta.bg, color: meta.tc }}
                >
                  {p.position === 'D/ST' ? 'DEF' : p.position}
                </span>
                <span className="min-w-0 flex-1 truncate text-[12.5px] font-medium">
                  {p.name}
                </span>
                <span className="text-[13px] font-semibold tabular-nums">
                  {p.total.toFixed(1)}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

/** Samples both teams' Gaussian score curves for the distribution chart. */
function distributionData(
  a: TeamPreviewStats,
  b: TeamPreviewStats,
): { x: number; a: number | null; b: number | null }[] | null {
  const sa = a.scoring;
  const sb = b.scoring;
  if (!sa && !sb) return null;
  const models = [sa, sb].filter((s): s is NonNullable<typeof s> => !!s);
  const lo = Math.min(...models.map((s) => s.mean - 3 * Math.max(s.std, 1)));
  const hi = Math.max(...models.map((s) => s.mean + 3 * Math.max(s.std, 1)));
  const pdf = (x: number, m: number, s: number): number => {
    const sig = Math.max(s, 1);
    return (
      Math.exp(-0.5 * ((x - m) / sig) ** 2) / (sig * Math.sqrt(2 * Math.PI))
    );
  };
  const steps = 48;
  const out: { x: number; a: number | null; b: number | null }[] = [];
  for (let i = 0; i <= steps; i++) {
    const x = lo + ((hi - lo) * i) / steps;
    out.push({
      x,
      a: sa ? pdf(x, sa.mean, sa.std) : null,
      b: sb ? pdf(x, sb.mean, sb.std) : null,
    });
  }
  return out;
}

function TrendChart({
  data,
  colorA,
  colorB,
  labelA,
  labelB,
}: {
  data: MatchupPreviewData;
  colorA: string;
  colorB: string;
  labelA: string;
  labelB: string;
}) {
  const chartData = useMemo(() => {
    const weeks = [
      ...new Set([
        ...data.teamA.weekly.map((w) => w.week),
        ...data.teamB.weekly.map((w) => w.week),
        ...data.leagueWeekly.map((w) => w.week),
      ]),
    ].sort((x, y) => x - y);
    return weeks.map((week) => ({
      week,
      a: data.teamA.weekly.find((w) => w.week === week)?.points ?? null,
      b: data.teamB.weekly.find((w) => w.week === week)?.points ?? null,
      league: data.leagueWeekly.find((w) => w.week === week)?.avg ?? null,
    }));
  }, [data]);

  const config: ChartConfig = {
    a: { label: labelA, color: colorA },
    b: { label: labelB, color: colorB },
    league: { label: 'League avg', color: 'var(--color-border)' },
  };

  if (chartData.length === 0) {
    return (
      <p className="py-6 text-center text-[12px] text-muted-foreground">
        No games played yet this season.
      </p>
    );
  }

  return (
    <ChartContainer config={config} className="h-56 w-full aspect-auto">
      <LineChart
        data={chartData}
        margin={{ top: 6, right: 6, left: 0, bottom: 4 }}
      >
        <CartesianGrid vertical={false} />
        <XAxis
          dataKey="week"
          tickFormatter={(v: number) => `Wk ${v}`}
          tickLine={false}
          axisLine={false}
          tickMargin={8}
        />
        <YAxis tickLine={false} axisLine={false} width={32} />
        <ChartTooltip content={<ChartTooltipContent indicator="line" />} />
        <Line
          type="monotone"
          dataKey="league"
          stroke="var(--color-border)"
          strokeWidth={2}
          strokeDasharray="4 4"
          dot={false}
          connectNulls
        />
        <Line
          type="monotone"
          dataKey="a"
          stroke={colorA}
          strokeWidth={2.5}
          dot={false}
          activeDot={{ r: 4 }}
          connectNulls
        />
        <Line
          type="monotone"
          dataKey="b"
          stroke={colorB}
          strokeWidth={2.5}
          dot={false}
          activeDot={{ r: 4 }}
          connectNulls
        />
      </LineChart>
    </ChartContainer>
  );
}

function DistributionChart({
  data,
  colorA,
  colorB,
  labelA,
  labelB,
}: {
  data: MatchupPreviewData;
  colorA: string;
  colorB: string;
  labelA: string;
  labelB: string;
}) {
  const curve = useMemo(() => distributionData(data.teamA, data.teamB), [data]);
  const config: ChartConfig = {
    a: { label: labelA, color: colorA },
    b: { label: labelB, color: colorB },
  };
  if (!curve) return null;
  return (
    <ChartContainer config={config} className="h-32 w-full aspect-auto">
      <AreaChart data={curve} margin={{ top: 6, right: 6, left: 6, bottom: 0 }}>
        <XAxis
          dataKey="x"
          type="number"
          domain={['dataMin', 'dataMax']}
          tickLine={false}
          axisLine={false}
          tickMargin={6}
          tickFormatter={(v: number) => String(Math.round(v))}
        />
        <Area
          type="monotone"
          dataKey="a"
          stroke={colorA}
          fill={colorA}
          fillOpacity={0.16}
          strokeWidth={2.5}
          isAnimationActive={false}
          connectNulls
        />
        <Area
          type="monotone"
          dataKey="b"
          stroke={colorB}
          fill={colorB}
          fillOpacity={0.16}
          strokeWidth={2.5}
          isAnimationActive={false}
          connectNulls
        />
        {/* Dotted vertical line at each team's mean (projected) score. */}
        {data.teamA.scoring && (
          <ReferenceLine
            x={data.teamA.scoring.mean}
            stroke={colorA}
            strokeDasharray="3 3"
            strokeOpacity={0.8}
          />
        )}
        {data.teamB.scoring && (
          <ReferenceLine
            x={data.teamB.scoring.mean}
            stroke={colorB}
            strokeDasharray="3 3"
            strokeOpacity={0.8}
          />
        )}
      </AreaChart>
    </ChartContainer>
  );
}

function TeamHeader({
  side,
  stats,
  align,
}: {
  side: PreviewSide;
  stats: TeamPreviewStats;
  align: 'left' | 'right';
}) {
  return (
    <div
      className={`flex items-center gap-2.5 ${align === 'right' ? 'flex-row-reverse text-right' : ''}`}
    >
      <TeamAvatar
        teamLogo={side.teamLogo}
        teamName={side.teamName}
        ownerUsername={side.ownerUsername}
        color={side.color}
        size="lg"
      />
      <div>
        <div className="text-[15px] font-semibold leading-tight">
          {side.ownerUsername}
        </div>
        <div className="text-[12px] text-muted-foreground">{side.teamName}</div>
        <span
          className="mt-1 inline-block rounded-full px-1.5 py-0.5 text-[11px] font-semibold tabular-nums"
          style={{ background: `${side.color}1a`, color: side.color }}
        >
          {stats.record}
        </span>
      </div>
    </div>
  );
}

const Card = ({
  children,
  className = '',
}: {
  children: ReactNode;
  className?: string;
}) => (
  <div
    className={`bg-card border border-border/50 rounded-lg overflow-hidden ${className}`}
  >
    {children}
  </div>
);

const SecLabel = ({ children }: { children: ReactNode }) => (
  <span className="mb-3 block text-[10px] font-semibold uppercase tracking-[0.07em] text-muted-foreground/70">
    {children}
  </span>
);

export function MatchupPreviewCard({
  left,
  right,
  data,
  onClose,
}: {
  left: PreviewSide;
  right: PreviewSide;
  data: MatchupPreviewData;
  onClose?: () => void;
}) {
  return (
    <div className="relative flex flex-col gap-3.5">
      {onClose && (
        <button
          onClick={onClose}
          className="absolute -top-3 -right-3 z-10 cursor-pointer rounded-full border border-border/50 bg-muted p-1.5 transition-colors hover:bg-muted/80"
          aria-label="Close preview"
        >
          <X className="h-3.5 w-3.5 text-muted-foreground" />
        </button>
      )}

      {/* Hero: win probability, projected score, distribution */}
      <Card className="p-5">
        <div className="grid grid-cols-[1fr_auto_1fr] items-start gap-4">
          <TeamHeader side={left} stats={data.teamA} align="left" />
          <span className="self-center pt-1 text-[11px] font-semibold uppercase tracking-[0.08em] text-muted-foreground/70">
            vs
          </span>
          <TeamHeader side={right} stats={data.teamB} align="right" />
        </div>

        <div className="mt-5">
          <div className="mb-1.5 flex items-baseline justify-between">
            <span
              className="text-[22px] font-bold tabular-nums"
              style={{ color: left.color }}
            >
              {pctLabel(data.winProbA)}
            </span>
            <span className="self-center text-[10px] font-semibold uppercase tracking-[0.07em] text-muted-foreground/70">
              Win probability
            </span>
            <span
              className="text-[22px] font-bold tabular-nums"
              style={{ color: right.color }}
            >
              {pctLabel(data.winProbB)}
            </span>
          </div>
          <div className="flex h-3 overflow-hidden rounded-full bg-muted">
            <div
              style={{
                width: `${data.winProbA * 100}%`,
                background: left.color,
              }}
            />
            <div
              style={{
                width: `${data.winProbB * 100}%`,
                background: right.color,
              }}
            />
          </div>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-2.5">
          <div className="flex flex-col gap-0.5 rounded-lg border border-border/50 bg-muted px-3 py-2.5">
            <span className="text-[10px] font-semibold uppercase tracking-[0.07em] text-muted-foreground/70">
              Projected
            </span>
            <span
              className="text-[21px] font-semibold tabular-nums"
              style={{ color: left.color }}
            >
              {data.projA !== null ? one(data.projA) : '—'}
            </span>
          </div>
          <div className="flex flex-col gap-0.5 rounded-lg border border-border/50 bg-muted px-3 py-2.5 text-right">
            <span className="text-[10px] font-semibold uppercase tracking-[0.07em] text-muted-foreground/70">
              Projected
            </span>
            <span
              className="text-[21px] font-semibold tabular-nums"
              style={{ color: right.color }}
            >
              {data.projB !== null ? one(data.projB) : '—'}
            </span>
          </div>
        </div>

        <div className="mt-4">
          <SecLabel>Projected score distribution</SecLabel>
          <DistributionChart
            data={data}
            colorA={left.color}
            colorB={right.color}
            labelA={left.ownerUsername}
            labelB={right.ownerUsername}
          />
        </div>
      </Card>

      <div className="grid grid-cols-1 gap-3.5 sm:grid-cols-2">
        {/* Head-to-head */}
        <Card className="p-4">
          <SecLabel>Head to head</SecLabel>
          <StatComparison
            a={data.teamA}
            b={data.teamB}
            colorA={left.color}
            colorB={right.color}
          />
        </Card>

        {/* Recent form */}
        <Card className="p-4">
          <SecLabel>Recent form</SecLabel>
          <div className="flex flex-col gap-3.5 divide-y divide-border/50 [&>*+*]:pt-3.5">
            <RecentForm side={left} stats={data.teamA} />
            <RecentForm side={right} stats={data.teamB} />
          </div>
        </Card>
      </div>

      {/* Points by week */}
      <Card className="p-4">
        <SecLabel>Points scored by week</SecLabel>
        <TrendChart
          data={data}
          colorA={left.color}
          colorB={right.color}
          labelA={left.ownerUsername}
          labelB={right.ownerUsername}
        />
      </Card>

      {/* Top scorers */}
      <Card className="p-4">
        <SecLabel>Top scorers this season</SecLabel>
        <div className="grid grid-cols-2">
          <TopScorersColumn side={left} stats={data.teamA} align="left" />
          <TopScorersColumn side={right} stats={data.teamB} align="right" />
        </div>
      </Card>
    </div>
  );
}
