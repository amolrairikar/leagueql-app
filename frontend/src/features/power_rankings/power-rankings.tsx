import {
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ChevronUp,
} from 'lucide-react';
import {
  Fragment,
  Suspense,
  use,
  useMemo,
  useState,
  type ReactNode,
} from 'react';

import {
  buildPowerRankings,
  POWER_COMPONENTS,
  type PowerRow,
  type Verdict,
} from './compute-power-rankings';

import { TeamAvatar } from '@/components/team-avatar';
import { Skeleton } from '@/components/ui/skeleton';
import {
  getSeasonMatchups,
  type MatchupItem,
} from '@/features/power_rankings/api-calls';
import SeasonSelect from '@/features/season_select/season-select';
import { UI_COLORS } from '@/lib/color-constants';
import { getLeagueCookies } from '@/lib/cookie-handler';
import { ErrorAlert } from '@/lib/error-alert';
import { buildTeamColorMap } from '@/lib/matchups';
import { type Result } from '@/lib/result';
import { latestSeason, seasonQuery } from '@/lib/season';
import { cn } from '@/lib/utils';

const POWER_RANKINGS_FALLBACK = 'Failed to load power rankings.';
const EMPTY_MESSAGE =
  'Power rankings will appear once games have been played this season.';

const HEADER_CELL =
  'text-[10px] font-medium uppercase tracking-[0.07em] text-muted-foreground px-3.5 py-2.5 border-b border-border/50 bg-muted';

const VERDICT_STYLES: Record<Verdict, { label: string; className: string }> = {
  underrated: {
    label: 'Underrated',
    className: 'text-green-700 dark:text-green-400',
  },
  overrated: {
    label: 'Overrated',
    className: 'text-red-700 dark:text-red-400',
  },
  'on-the-mark': {
    label: 'On the mark',
    className: 'text-muted-foreground',
  },
};

function signed(n: number): string {
  const rounded = Math.round(n);
  if (rounded === 0) return '0';
  return `${rounded > 0 ? '+' : '−'}${Math.abs(rounded)}`;
}

function Movement({ movement }: { movement: number }) {
  if (movement === 0) {
    return (
      <span className="text-muted-foreground pl-2" aria-label="No movement">
        &ndash;
      </span>
    );
  }
  const up = movement > 0;
  const Icon = up ? ChevronUp : ChevronDown;
  return (
    <span
      className={cn(
        'inline-flex items-center gap-0.5 rounded-full py-0.5 pl-1 pr-2 text-[12px] font-semibold',
        up
          ? 'bg-green-50 text-green-700 dark:bg-green-950 dark:text-green-400'
          : 'bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-400',
      )}
      aria-label={`${up ? 'Up' : 'Down'} ${Math.abs(movement)}`}
    >
      <Icon className="size-3.5" strokeWidth={3} aria-hidden="true" />
      {Math.abs(movement)}
    </span>
  );
}

function RankTrend({
  trend,
  teamCount,
}: {
  trend: number[];
  teamCount: number;
}) {
  const width = 80;
  const height = 24;
  const x = (i: number) =>
    trend.length === 1 ? width / 2 : 4 + (i * (width - 8)) / (trend.length - 1);
  const y = (rank: number) =>
    teamCount <= 1
      ? height / 2
      : 3 + ((rank - 1) / (teamCount - 1)) * (height - 6);
  const points = trend.map((r, i) => `${x(i).toFixed(1)},${y(r).toFixed(1)}`);
  const last = trend.length - 1;

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-label={`Rank over the last ${trend.length} week${trend.length === 1 ? '' : 's'}, from ${trend[0]} to ${trend[last]}`}
    >
      {trend.length > 1 && (
        <polyline
          points={points.join(' ')}
          fill="none"
          className="stroke-muted-foreground/60"
          strokeWidth={1.5}
          strokeLinejoin="round"
          strokeLinecap="round"
        />
      )}
      <circle
        cx={x(last)}
        cy={y(trend[last])}
        r={3.5}
        className="fill-primary"
      />
    </svg>
  );
}

function Breakdown({ row }: { row: PowerRow }) {
  return (
    <div className="flex flex-wrap gap-x-10 gap-y-5 px-3.5 py-4 bg-muted/40">
      <div className="flex-1 basis-80 flex flex-col gap-2.5">
        <p className="text-[10px] font-medium uppercase tracking-[0.07em] text-muted-foreground">
          What drives this score
        </p>
        {row.components.map((c) => (
          <div
            key={c.key}
            className="grid grid-cols-[110px_1fr_36px_44px] items-center gap-3 text-[12px]"
          >
            <span className="font-medium text-foreground">{c.label}</span>
            <div className="h-1.5 rounded-full bg-border overflow-hidden">
              <div
                className="h-full rounded-full bg-chart-2"
                style={{ width: `${Math.round(c.value ?? 0)}%` }}
              />
            </div>
            <span className="text-right font-semibold text-foreground">
              {c.value === null ? 'n/a' : Math.round(c.value)}
            </span>
            <span
              className={cn(
                'text-right font-semibold',
                c.delta === null || Math.round(c.delta) === 0
                  ? 'text-muted-foreground'
                  : c.delta > 0
                    ? 'text-green-700 dark:text-green-400'
                    : 'text-red-700 dark:text-red-400',
              )}
            >
              {c.delta === null ? '' : signed(c.delta)}
            </span>
          </div>
        ))}
      </div>
      <div className="flex-1 basis-64 flex flex-col gap-2">
        <p className="text-[10px] font-medium uppercase tracking-[0.07em] text-muted-foreground">
          Read on the team
        </p>
        <p className="text-[13px] leading-relaxed text-foreground">
          {row.blurb}
        </p>
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-[12px] text-muted-foreground mt-1">
          <span>
            Expected record{' '}
            <strong className="text-foreground">{row.expectedRecord}</strong>
          </span>
          <span>
            Last week{' '}
            <strong className="text-foreground">
              {row.prevRank === null ? '–' : `#${row.prevRank}`}
            </strong>
          </span>
        </div>
      </div>
    </div>
  );
}

function FormulaSection() {
  const [open, setOpen] = useState(false);
  const Chevron = open ? ChevronUp : ChevronDown;
  return (
    <section
      aria-label="How power rankings are calculated"
      className="bg-card border border-border/50 rounded-lg mb-6"
    >
      <h2 className="m-0">
        <button
          type="button"
          aria-expanded={open}
          aria-controls="power-rankings-formula"
          className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left text-[14px] font-medium text-foreground cursor-pointer"
          onClick={() => setOpen(!open)}
        >
          How power rankings are calculated
          <Chevron
            className="size-4 shrink-0 text-muted-foreground"
            aria-hidden="true"
          />
        </button>
      </h2>
      {open && (
        <div id="power-rankings-formula" className="px-4 pb-4">
          <p className="text-[13px] text-muted-foreground leading-relaxed max-w-prose mb-3.5">
            Each team is scored 0&ndash;100 on four measures. The power score is
            a weighted average of the four, and teams are ranked by it. Rank
            movement compares this week&rsquo;s rank to last week&rsquo;s.
          </p>
          <div className="grid grid-cols-[repeat(auto-fit,minmax(220px,1fr))] gap-2.5">
            {POWER_COMPONENTS.map((c) => (
              <div key={c.key} className="rounded-md bg-muted px-3.5 py-3">
                <div className="flex items-baseline justify-between gap-2">
                  <span className="text-[13px] font-medium text-foreground">
                    {c.label}
                  </span>
                  <span className="text-[15px] font-semibold text-primary">
                    {c.weight}%
                  </span>
                </div>
                <p className="text-[12px] text-muted-foreground leading-snug mt-1">
                  {c.description}
                </p>
              </div>
            ))}
          </div>
          <ScalingExample />
        </div>
      )}
    </section>
  );
}

/** Season point totals for the worked scaling example. */
const SCALING_EXAMPLE_TEAMS = [
  { team: 'Amy', points: 410 },
  { team: 'Ben', points: 360 },
  { team: 'Cal', points: 330 },
  { team: 'Dee', points: 250 },
];

function ScalingExample() {
  const totals = SCALING_EXAMPLE_TEAMS.map((t) => t.points);
  const lowest = Math.min(...totals);
  const highest = Math.max(...totals);
  const cell = 'px-3 py-2 border-b border-border/50';
  const head = `${cell} text-[10px] font-medium uppercase tracking-[0.07em] text-muted-foreground bg-muted`;

  return (
    <div className="mt-5 border-t border-border/50 pt-4">
      <h3 className="text-[13px] font-medium text-foreground mb-1">
        How scaling works
      </h3>
      <p className="text-[13px] text-muted-foreground leading-relaxed max-w-prose mb-3">
        Points scored, recent form and lineup efficiency are measured in
        different units, so each is scaled across the league before the four
        measures are blended. A team&rsquo;s scaled score is its value&rsquo;s
        position between the league&rsquo;s lowest and highest values:
      </p>
      <p className="text-[13px] font-medium text-foreground mb-3">
        (your value &minus; lowest) &divide; (highest &minus; lowest) &times;
        100
      </p>
      <p className="text-[12px] text-muted-foreground mb-2">
        Example: season points after three weeks. The league low is {lowest} and
        the league high is {highest}, a spread of {highest - lowest}.
      </p>
      <div className="overflow-x-auto rounded-md border border-border/50">
        <table className="w-full border-separate border-spacing-0 text-[12px]">
          <thead>
            <tr>
              <th className={cn(head, 'text-left')}>Team</th>
              <th className={cn(head, 'text-right')}>Points</th>
              <th className={cn(head, 'text-left')}>Calculation</th>
              <th className={cn(head, 'text-right')}>Scaled score</th>
            </tr>
          </thead>
          <tbody>
            {SCALING_EXAMPLE_TEAMS.map(({ team, points }) => {
              const scaled = ((points - lowest) / (highest - lowest)) * 100;
              return (
                <tr key={team}>
                  <td className={cn(cell, 'font-medium text-foreground')}>
                    {team}
                  </td>
                  <td className={cn(cell, 'text-right text-foreground')}>
                    {points}
                  </td>
                  <td className={cn(cell, 'text-muted-foreground')}>
                    ({points} &minus; {lowest}) &divide; {highest - lowest}{' '}
                    &times; 100
                  </td>
                  <td
                    className={cn(
                      cell,
                      'text-right font-semibold text-foreground',
                    )}
                  >
                    {Number(scaled.toFixed(1))}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <ul className="mt-3 list-disc pl-5 space-y-1 text-[12px] text-muted-foreground leading-snug">
        <li>The highest value always scores 100 and the lowest scores 0.</li>
        <li>
          If every team has the same value, each team scores 50 for that
          measure.
        </li>
        <li>
          Scores are recalculated every week, so a team&rsquo;s scaled score can
          move even when its own total did not change.
        </li>
        <li>
          The scaled score is then multiplied by the measure&rsquo;s weight.
          Amy&rsquo;s 100 in points scored adds 30 points to her power score.
        </li>
      </ul>
    </div>
  );
}

function RankingsTable({
  rows,
  colorMap,
}: {
  rows: PowerRow[];
  colorMap: Map<string, string>;
}) {
  const [openId, setOpenId] = useState<string | null>(null);

  return (
    <div className="bg-card border border-border/50 rounded-lg overflow-hidden">
      <div className="max-h-[75vh] overflow-auto">
        <table
          className="w-full border-separate border-spacing-0 text-[13px]"
          style={{ minWidth: '820px' }}
        >
          <thead className="sticky top-0 z-10">
            <tr>
              <th className={cn(HEADER_CELL, 'text-left w-14')}>Rank</th>
              <th className={cn(HEADER_CELL, 'text-left w-20')}>Move</th>
              <th className={cn(HEADER_CELL, 'text-left')}>Team</th>
              <th className={cn(HEADER_CELL, 'text-right w-20')}>Record</th>
              <th className={cn(HEADER_CELL, 'text-left w-52')}>Power score</th>
              <th className={cn(HEADER_CELL, 'text-left w-24')}>Trend</th>
              <th className={cn(HEADER_CELL, 'text-left w-28')}>Record rank</th>
              <th className={cn(HEADER_CELL, 'w-10')}>
                <span className="sr-only">Details</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const open = openId === row.teamId;
              const verdict = VERDICT_STYLES[row.verdict];
              const toggle = () => setOpenId(open ? null : row.teamId);
              const Chevron = open ? ChevronUp : ChevronDown;
              return (
                <Fragment key={row.teamId}>
                  <tr
                    className={cn(
                      'cursor-pointer transition-colors',
                      open ? 'bg-muted/60' : 'hover:bg-muted/40',
                    )}
                    onClick={toggle}
                  >
                    <td className="px-3.5 py-3 border-b border-border/50 text-[18px] font-bold text-foreground">
                      {row.rank}
                    </td>
                    <td className="px-3.5 py-3 border-b border-border/50">
                      <Movement movement={row.movement} />
                    </td>
                    <td className="px-3.5 py-3 border-b border-border/50">
                      <div className="flex items-center gap-2.5 min-w-0">
                        <TeamAvatar
                          teamLogo={row.teamLogo}
                          teamName={row.teamName}
                          ownerUsername={row.managerName}
                          color={colorMap.get(row.teamId) ?? UI_COLORS.default}
                        />
                        <div className="min-w-0">
                          <div className="font-medium text-foreground truncate">
                            {row.teamName}
                          </div>
                          <div className="text-[12px] text-muted-foreground truncate">
                            {row.managerName}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="px-3.5 py-3 border-b border-border/50 text-right text-foreground">
                      {row.record}
                    </td>
                    <td className="px-3.5 py-3 border-b border-border/50">
                      <div className="flex items-center gap-2.5">
                        <div className="flex-1 h-2 rounded-full bg-muted overflow-hidden">
                          <div
                            className="h-full rounded-full bg-primary"
                            style={{
                              width: `${Math.max(2, Math.round(row.score))}%`,
                            }}
                          />
                        </div>
                        <span className="w-8 text-right font-semibold text-foreground">
                          {Math.round(row.score)}
                        </span>
                      </div>
                    </td>
                    <td className="px-3.5 py-3 border-b border-border/50">
                      <RankTrend trend={row.trend} teamCount={rows.length} />
                    </td>
                    <td className="px-3.5 py-3 border-b border-border/50">
                      <div className="text-foreground">#{row.recordRank}</div>
                      <div
                        className={cn(
                          'text-[11px] font-semibold',
                          verdict.className,
                        )}
                      >
                        {verdict.label}
                      </div>
                    </td>
                    <td className="px-3.5 py-3 border-b border-border/50 text-muted-foreground">
                      <button
                        type="button"
                        aria-expanded={open}
                        aria-label={`${open ? 'Hide' : 'Show'} details for ${row.teamName}`}
                        className="flex size-6 items-center justify-center rounded cursor-pointer"
                        onClick={(e) => {
                          e.stopPropagation();
                          toggle();
                        }}
                      >
                        <Chevron className="size-4" aria-hidden="true" />
                      </button>
                    </td>
                  </tr>
                  {open && (
                    <tr>
                      <td colSpan={8} className="p-0 border-b border-border/50">
                        <Breakdown row={row} />
                      </td>
                    </tr>
                  )}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function WeekStepper({
  weeks,
  value,
  onChange,
}: {
  weeks: number[];
  value: number;
  onChange: (week: number) => void;
}) {
  const index = weeks.indexOf(value);
  const buttonClass =
    'flex size-8 items-center justify-center rounded-md text-foreground cursor-pointer hover:bg-muted disabled:cursor-not-allowed disabled:text-muted-foreground/50 disabled:hover:bg-transparent';
  return (
    <div className="inline-flex items-center rounded-lg border border-border/50 bg-card p-0.5">
      <button
        type="button"
        aria-label="Previous week"
        className={buttonClass}
        disabled={index <= 0}
        onClick={() => onChange(weeks[index - 1])}
      >
        <ChevronLeft className="size-4" aria-hidden="true" />
      </button>
      <span className="min-w-20 text-center text-[13px] font-medium text-foreground">
        Week {value}
      </span>
      <button
        type="button"
        aria-label="Next week"
        className={buttonClass}
        disabled={index === -1 || index >= weeks.length - 1}
        onClick={() => onChange(weeks[index + 1])}
      >
        <ChevronRight className="size-4" aria-hidden="true" />
      </button>
    </div>
  );
}

function SkeletonRankings() {
  return (
    <div className="bg-card border border-border/50 rounded-lg overflow-hidden">
      <div className="bg-muted h-9 border-b border-border/50" />
      {Array.from({ length: 8 }).map((_, i) => (
        <div
          key={i}
          className="flex items-center gap-4 px-3.5 py-3 border-b border-border/50 last:border-0"
        >
          <Skeleton className="h-5 w-6" />
          <Skeleton className="h-6 w-6 rounded-full" />
          <Skeleton className="h-4 w-40" />
          <Skeleton className="h-2 flex-1" />
        </div>
      ))}
    </div>
  );
}

function RankingsContent({
  promise,
  seasonSelect,
}: {
  promise: Promise<Result<MatchupItem[]>>;
  seasonSelect: ReactNode;
}) {
  const result = use(promise);
  const matchups = useMemo(() => (result.ok ? result.data : []), [result]);

  const rankings = useMemo(() => buildPowerRankings(matchups), [matchups]);
  const colorMap = useMemo(() => buildTeamColorMap(matchups), [matchups]);

  // Week N ranks teams on games through week N-1, so the selectable weeks are
  // the second played week through the week after the last played one.
  const { playedWeeks } = rankings;
  const weeks = useMemo(
    () =>
      playedWeeks.length === 0
        ? []
        : [...playedWeeks.slice(1), playedWeeks[playedWeeks.length - 1] + 1],
    [playedWeeks],
  );
  const defaultWeek = weeks[weeks.length - 1];
  const [selectedWeek, setSelectedWeek] = useState<number | null>(null);
  const week = selectedWeek ?? defaultWeek;

  const rows = useMemo(() => {
    if (week === undefined) return [];
    const throughIndex = weeks.indexOf(week);
    return rankings.through(playedWeeks[throughIndex]);
  }, [rankings, playedWeeks, weeks, week]);

  if (!result.ok) {
    return (
      <>
        <div className="mb-4">{seasonSelect}</div>
        <ErrorAlert message={result.error} />
      </>
    );
  }

  return (
    <>
      <div className="flex flex-wrap items-center gap-2.5 mb-5">
        {seasonSelect}
        {week !== undefined && (
          <WeekStepper weeks={weeks} value={week} onChange={setSelectedWeek} />
        )}
      </div>
      <FormulaSection />
      {rows.length === 0 ? (
        <p className="text-[13px] text-muted-foreground text-center py-12">
          {EMPTY_MESSAGE}
        </p>
      ) : (
        <RankingsTable rows={rows} colorMap={colorMap} />
      )}
    </>
  );
}

export default function PowerRankings() {
  const { leagueId, platform, seasons } = useMemo(() => getLeagueCookies(), []);
  const [selectedSeason, setSelectedSeason] = useState(latestSeason(seasons));

  const promise = useMemo(
    (): Promise<Result<MatchupItem[]>> =>
      seasonQuery(
        Boolean(leagueId && selectedSeason),
        () => getSeasonMatchups(leagueId, platform, selectedSeason),
        POWER_RANKINGS_FALLBACK,
      ),
    [leagueId, platform, selectedSeason],
  );

  const seasonSelect =
    seasons.length > 0 ? (
      <SeasonSelect
        seasons={seasons}
        value={selectedSeason}
        onValueChange={setSelectedSeason}
      />
    ) : null;

  return (
    <div className="flex flex-1 flex-col p-6 overflow-auto">
      <div className="max-w-225 mx-auto w-full">
        <Suspense
          fallback={
            <>
              <div className="mb-4">{seasonSelect}</div>
              <SkeletonRankings />
            </>
          }
        >
          {/* Keyed by season so the week picker resets to its default on a season change. */}
          <RankingsContent
            key={selectedSeason}
            promise={promise}
            seasonSelect={seasonSelect}
          />
        </Suspense>
      </div>
    </div>
  );
}
