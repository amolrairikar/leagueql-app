import {
  ArrowDown,
  ArrowDownRight,
  ArrowUp,
  Calendar,
  Dices,
  Flame,
  Gauge,
  Gem,
  Layers,
  Minus,
  Snowflake,
  TrendingUp,
  Trophy,
  type LucideIcon,
} from 'lucide-react';
import { Suspense, use, useMemo, useState } from 'react';

import { type MyTeamData, getMyTeamData } from './api-calls';
import { type GradeResult } from './compute-grade';
import {
  type Insight,
  computeInsights,
  heroVerdict,
  ordinal,
} from './compute-insights';
import { type TeamMetrics, computeTeamMetrics } from './compute-team-metrics';

import type { Platform } from '@/components/api/types';
import { TeamAvatar } from '@/components/team-avatar';
import { Skeleton } from '@/components/ui/skeleton';
import SeasonSelect from '@/features/season_select/season-select';
import { avatarColor } from '@/lib/color-constants';
import {
  getLeagueCookies,
  getMyTeamOwnerId,
  setMyTeamOwnerId,
} from '@/lib/cookie-handler';
import { ErrorAlert } from '@/lib/error-alert';
import { type Result, toResult } from '@/lib/result';

type MyTeamResult = Result<MyTeamData>;

// ── Sentiment styling for insight cards ─────────────────────────────────────────

const SENTIMENT_ICON_CLASS: Record<Insight['sentiment'], string> = {
  good: 'text-emerald-600 dark:text-emerald-400 bg-emerald-500/10',
  warn: 'text-amber-600 dark:text-amber-400 bg-amber-500/10',
  bad: 'text-red-600 dark:text-red-400 bg-red-500/10',
};
const SENTIMENT_BORDER: Record<Insight['sentiment'], string> = {
  good: 'border-l-emerald-500',
  warn: 'border-l-amber-500',
  bad: 'border-l-red-500',
};
const SENTIMENT_TEXT: Record<Insight['sentiment'], string> = {
  good: 'text-emerald-600 dark:text-emerald-400',
  warn: 'text-amber-600 dark:text-amber-400',
  bad: 'text-red-600 dark:text-red-400',
};
const INSIGHT_ICON: Record<string, LucideIcon> = {
  unlucky: Dices,
  lucky: Dices,
  'best-trade': Trophy,
  'trade-regret': ArrowDownRight,
  'bench-leak': Layers,
  'lineup-sharp': Gauge,
  'draft-steal': Gem,
  'draft-bust': ArrowDownRight,
  'elite-scoring': Flame,
  'all-play-over': TrendingUp,
  'tough-schedule': Calendar,
  'hot-streak': Flame,
  'cold-streak': Snowflake,
};

// ── Small building blocks ───────────────────────────────────────────────────────

const SECTION_LABEL =
  'text-[11px] font-medium uppercase tracking-[0.08em] text-muted-foreground mb-2.5';
const PANEL = 'bg-card border border-border/50 rounded-lg';

function MovementChip({ movement }: { movement: number }) {
  if (movement > 0) {
    return (
      <span className="inline-flex items-center gap-0.5 text-[11px] font-semibold text-emerald-600 dark:text-emerald-400">
        <ArrowUp className="h-3 w-3" />
        {movement}
      </span>
    );
  }
  if (movement < 0) {
    return (
      <span className="inline-flex items-center gap-0.5 text-[11px] font-semibold text-red-600 dark:text-red-400">
        <ArrowDown className="h-3 w-3" />
        {Math.abs(movement)}
      </span>
    );
  }
  return (
    <span className="inline-flex items-center text-[11px] font-semibold text-muted-foreground">
      <Minus className="h-3 w-3" />
    </span>
  );
}

function GradeBadge({
  grade,
  size = 'sm',
}: {
  grade: GradeResult | null;
  size?: 'sm' | 'lg';
}) {
  const dims =
    size === 'lg'
      ? 'w-[76px] h-[76px] rounded-2xl text-[34px]'
      : 'w-11 h-11 rounded-xl text-xl';
  return (
    <div
      className={`flex items-center justify-center font-bold tracking-tight shrink-0 text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 ${dims}`}
    >
      {grade?.letter ?? '—'}
    </div>
  );
}

function Stat({
  label,
  value,
  sub,
  subNode,
}: {
  label: string;
  value: string;
  sub?: string;
  subNode?: React.ReactNode;
}) {
  return (
    <div className={`${PANEL} p-3 text-center`}>
      <div className="text-[10px] font-semibold uppercase tracking-[0.05em] text-muted-foreground mb-1">
        {label}
      </div>
      <div className="text-[21px] font-bold leading-none tabular-nums">
        {value}
      </div>
      <div className="text-[10.5px] text-muted-foreground mt-1 min-h-[14px]">
        {subNode ?? sub ?? ' '}
      </div>
    </div>
  );
}

function Meter({
  label,
  value,
  pct,
  color,
}: {
  label: string;
  value: string;
  pct: number;
  color: string;
}) {
  return (
    <div className="flex flex-col gap-1.5 mb-3.5 last:mb-0">
      <div className="flex justify-between text-[12px]">
        <span>{label}</span>
        <span className="font-medium tabular-nums">{value}</span>
      </div>
      <div className="h-[7px] rounded-full bg-muted overflow-hidden">
        <span
          className="block h-full rounded-full"
          style={{
            width: `${Math.max(0, Math.min(100, pct))}%`,
            background: color,
          }}
        />
      </div>
    </div>
  );
}

// ── Sections ────────────────────────────────────────────────────────────────────

function Hero({
  m,
  color,
  verdict,
}: {
  m: TeamMetrics;
  color: string;
  verdict: string;
}) {
  return (
    <div className={`${PANEL} p-5 mb-4`}>
      <div className="flex items-start gap-4">
        <TeamAvatar
          teamLogo={m.teamLogo}
          teamName={m.teamName}
          ownerUsername={m.ownerUsername}
          color={color}
          size="lg"
        />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2.5 flex-wrap">
            <h1 className="text-xl font-bold tracking-tight m-0">
              {m.teamName || `Team ${m.ownerUsername}`}
            </h1>
            {m.powerRank && (
              <span className="inline-flex items-center gap-1.5 text-[11px] font-semibold px-2 py-0.5 rounded-full text-primary bg-primary/10">
                {ordinal(m.powerRank.rank)} in power rankings
                <MovementChip movement={m.powerRank.movement} />
              </span>
            )}
          </div>
          <p className="text-[13.5px] leading-relaxed text-foreground/85 max-w-[60ch] mt-2.5 mb-0">
            {verdict}
          </p>
        </div>
        <GradeBadge grade={m.grade} size="sm" />
      </div>
    </div>
  );
}

function KpiRow({ m }: { m: TeamMetrics }) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5 mb-6">
      <Stat label="Record" value={m.record} sub={m.winPct.toFixed(3)} />
      <Stat label="Standing" value={ordinal(m.seed)} sub={`of ${m.numTeams}`} />
      <Stat
        label="Power rank"
        value={m.powerRank ? ordinal(m.powerRank.rank) : '—'}
        subNode={
          m.powerRank ? <MovementChip movement={m.powerRank.movement} /> : ' '
        }
      />
      <Stat
        label="Points for"
        value={Math.round(m.totalPf).toLocaleString()}
        sub={`${ordinal(m.pfRank)} most`}
      />
      <Stat
        label="All-play"
        value={`${m.allPlayWins}-${m.allPlayLosses}`}
        sub={m.allPlayWinPct.toFixed(3)}
      />
      <Stat
        label="Luck"
        value={
          m.luck !== null ? (m.luck >= 0 ? '+' : '') + m.luck.toFixed(1) : '—'
        }
        sub="wins vs exp."
      />
    </div>
  );
}

function RecentForm({ m }: { m: TeamMetrics }) {
  return (
    <div>
      <p className={SECTION_LABEL}>Recent form</p>
      <div className={PANEL}>
        {m.recentForm.length === 0 ? (
          <p className="text-[13px] text-muted-foreground text-center py-8">
            No games played yet.
          </p>
        ) : (
          m.recentForm.map((g) => (
            <div
              key={g.week}
              className="flex items-center gap-2.5 px-3.5 py-2.5 border-b border-border/50 last:border-0"
            >
              <span
                className={`w-5 h-5 rounded-md text-[11px] font-bold flex items-center justify-center text-white shrink-0 ${
                  g.result === 'W'
                    ? 'bg-emerald-600'
                    : g.result === 'L'
                      ? 'bg-red-600'
                      : 'bg-muted-foreground'
                }`}
              >
                {g.result}
              </span>
              <span className="text-[12.5px] text-muted-foreground truncate">
                Wk {g.week} · vs {g.opponent}
              </span>
              <span className="ml-auto text-[12.5px] font-semibold tabular-nums shrink-0">
                {g.teamScore.toFixed(1)}–{g.oppScore.toFixed(1)}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

function StackUp({ m }: { m: TeamMetrics }) {
  const pfPct =
    m.numTeams > 1 ? ((m.numTeams - m.pfRank + 1) / m.numTeams) * 100 : 100;
  const sosPct =
    m.sosRank !== null && m.numTeams > 1
      ? ((m.numTeams - m.sosRank + 1) / m.numTeams) * 100
      : 50;
  const winPctBar = m.gamesPlayed > 0 ? (m.wins / m.gamesPlayed) * 100 : 0;
  return (
    <div>
      <p className={SECTION_LABEL}>How you stack up</p>
      <div className={`${PANEL} p-5`}>
        <Meter
          label="Points for"
          value={`${ordinal(m.pfRank)} of ${m.numTeams}`}
          pct={pfPct}
          color="#059669"
        />
        <Meter
          label="Lineup efficiency"
          value={
            m.efficiency !== null ? `${(m.efficiency * 100).toFixed(1)}%` : '—'
          }
          pct={m.efficiency !== null ? m.efficiency * 100 : 0}
          color="var(--primary)"
        />
        <Meter
          label="Strength of schedule"
          value={
            m.sos !== null
              ? `${m.sos.toFixed(3)}${m.sosRank === 1 ? ' · hardest' : ''}`
              : '—'
          }
          pct={sosPct}
          color="#b45309"
        />
        <Meter
          label="Expected wins"
          value={
            m.expectedWins !== null
              ? `${m.expectedWins.toFixed(1)} vs ${m.wins} actual`
              : '—'
          }
          pct={winPctBar}
          color={m.luck !== null && m.luck < 0 ? '#c0392b' : '#059669'}
        />
      </div>
    </div>
  );
}

function DraftReport({ m }: { m: TeamMetrics }) {
  const { bestPick, worstPick, steals, busts } = m.draft;
  const pickLabel = (round: number, overall: number) =>
    `Round ${round}, pick ${overall}`;
  return (
    <div>
      <p className={SECTION_LABEL}>Draft report</p>
      <div className={PANEL}>
        {!bestPick && !worstPick ? (
          <p className="text-[13px] text-muted-foreground text-center py-8">
            No draft data for this team.
          </p>
        ) : (
          <>
            {bestPick && (
              <div className="flex items-start gap-3 px-4 py-3 border-b border-border/50">
                <div className="w-[34px] h-[34px] rounded-lg flex items-center justify-center shrink-0 text-emerald-600 dark:text-emerald-400 bg-emerald-500/10">
                  <Gem className="h-[18px] w-[18px]" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-[10.5px] font-semibold uppercase tracking-[0.06em] text-emerald-600 dark:text-emerald-400 mb-0.5">
                    Best pick
                    {(bestPick.draft_rank_delta ?? 0) >= 5 ? ' · steal' : ''}
                  </div>
                  <div className="text-[13.5px] font-semibold">
                    {bestPick.player_name ?? '—'}
                  </div>
                  <div className="text-[12px] text-muted-foreground">
                    {pickLabel(bestPick.round, bestPick.overall_pick_number)}
                    {bestPick.actual_position_rank !== null
                      ? ` · ${bestPick.position}${bestPick.actual_position_rank}`
                      : ''}
                  </div>
                </div>
                <div className="text-[12px] font-bold tabular-nums text-emerald-600 dark:text-emerald-400">
                  {(bestPick.draft_rank_delta ?? 0) >= 0 ? '+' : ''}
                  {bestPick.draft_rank_delta}
                </div>
              </div>
            )}
            {worstPick && (
              <div className="flex items-start gap-3 px-4 py-3 border-b border-border/50">
                <div className="w-[34px] h-[34px] rounded-lg flex items-center justify-center shrink-0 text-red-600 dark:text-red-400 bg-red-500/10">
                  <ArrowDownRight className="h-[18px] w-[18px]" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-[10.5px] font-semibold uppercase tracking-[0.06em] text-red-600 dark:text-red-400 mb-0.5">
                    Worst pick
                  </div>
                  <div className="text-[13.5px] font-semibold">
                    {worstPick.player_name ?? '—'}
                  </div>
                  <div className="text-[12px] text-muted-foreground">
                    {pickLabel(worstPick.round, worstPick.overall_pick_number)}
                    {worstPick.actual_position_rank !== null
                      ? ` · ${worstPick.position}${worstPick.actual_position_rank}`
                      : ''}
                  </div>
                </div>
                <div className="text-[12px] font-bold tabular-nums text-red-600 dark:text-red-400">
                  {worstPick.draft_rank_delta}
                </div>
              </div>
            )}
            <div className="flex items-center justify-between px-4 py-3 text-[12.5px] text-muted-foreground">
              <span>
                {steals} steal{steals === 1 ? '' : 's'} · {busts} bust
                {busts === 1 ? '' : 's'}
              </span>
              <a
                href="/draft_grades"
                className="text-primary font-semibold text-[12px]"
              >
                Open Draft Grades →
              </a>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function TradeReport({ m }: { m: TeamMetrics }) {
  const gated = m.platform !== 'SLEEPER';
  const { best, worst, tradeCount, waiverCount } = m.trades;
  return (
    <div>
      <p className={SECTION_LABEL}>Trade report</p>
      <div className={PANEL}>
        {gated ? (
          <p className="text-[13px] text-muted-foreground text-center py-8 px-4">
            Transactions are available on Sleeper leagues.
          </p>
        ) : !best && !worst ? (
          <p className="text-[13px] text-muted-foreground text-center py-8">
            No trades this season.
          </p>
        ) : (
          <>
            {best && (
              <div className="flex items-start gap-3 px-4 py-3 border-b border-border/50">
                <div className="w-[34px] h-[34px] rounded-lg flex items-center justify-center shrink-0 text-emerald-600 dark:text-emerald-400 bg-emerald-500/10">
                  <Trophy className="h-[18px] w-[18px]" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-[10.5px] font-semibold uppercase tracking-[0.06em] text-emerald-600 dark:text-emerald-400 mb-0.5">
                    {best.net >= 0 ? 'Best trade · won' : 'Best trade'}
                  </div>
                  <div className="text-[13.5px] font-semibold">
                    Got {best.acquired.join(', ') || '—'}
                  </div>
                  <div className="text-[12px] text-muted-foreground">
                    Gave {best.gaveUp.join(', ') || '—'} · since Wk {best.week}
                  </div>
                </div>
                <div className="text-[12px] font-bold tabular-nums text-emerald-600 dark:text-emerald-400">
                  {best.net >= 0 ? '+' : ''}
                  {best.net.toFixed(1)}
                </div>
              </div>
            )}
            {worst && (
              <div className="flex items-start gap-3 px-4 py-3 border-b border-border/50">
                <div className="w-[34px] h-[34px] rounded-lg flex items-center justify-center shrink-0 text-red-600 dark:text-red-400 bg-red-500/10">
                  <ArrowDownRight className="h-[18px] w-[18px]" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-[10.5px] font-semibold uppercase tracking-[0.06em] text-red-600 dark:text-red-400 mb-0.5">
                    Worst trade
                  </div>
                  <div className="text-[13.5px] font-semibold">
                    Got {worst.acquired.join(', ') || '—'}
                  </div>
                  <div className="text-[12px] text-muted-foreground">
                    Gave {worst.gaveUp.join(', ') || '—'} · since Wk{' '}
                    {worst.week}
                  </div>
                </div>
                <div className="text-[12px] font-bold tabular-nums text-red-600 dark:text-red-400">
                  {worst.net.toFixed(1)}
                </div>
              </div>
            )}
            <div className="flex items-center justify-between px-4 py-3 text-[12.5px] text-muted-foreground">
              <span>
                {tradeCount} trade{tradeCount === 1 ? '' : 's'} · {waiverCount}{' '}
                waiver claim{waiverCount === 1 ? '' : 's'}
              </span>
              <a
                href="/transactions"
                className="text-primary font-semibold text-[12px]"
              >
                Open Transactions →
              </a>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function Insights({ insights }: { insights: Insight[] }) {
  if (insights.length === 0) return null;
  return (
    <div>
      <p className={SECTION_LABEL}>Insights</p>
      <div className="flex flex-col gap-2.5">
        {insights.map((ins) => {
          const Icon = INSIGHT_ICON[ins.id] ?? TrendingUp;
          return (
            <div
              key={ins.id}
              className={`grid grid-cols-[40px_1fr_auto] gap-3.5 items-start p-4 bg-card border border-border/50 border-l-[3px] rounded-lg ${SENTIMENT_BORDER[ins.sentiment]}`}
            >
              <div
                className={`w-10 h-10 rounded-[10px] flex items-center justify-center ${SENTIMENT_ICON_CLASS[ins.sentiment]}`}
              >
                <Icon className="h-[19px] w-[19px]" />
              </div>
              <div className="min-w-0">
                <div
                  className={`text-[10px] font-bold uppercase tracking-[0.06em] mb-1 ${SENTIMENT_TEXT[ins.sentiment]}`}
                >
                  {ins.tag}
                </div>
                <h3 className="m-0 mb-1 text-[14.5px] font-semibold tracking-[-0.005em]">
                  {ins.headline}
                </h3>
                <p className="m-0 text-[12.5px] leading-relaxed text-muted-foreground max-w-[56ch]">
                  {ins.sentence}
                </p>
              </div>
              <div className="text-right shrink-0 tabular-nums">
                <div className="text-[20px] font-bold leading-none tracking-[-0.01em]">
                  {ins.metric.value}
                </div>
                <div className="text-[10px] text-muted-foreground mt-1">
                  {ins.metric.cap}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Manager roster + selection ──────────────────────────────────────────────────

interface Manager {
  ownerId: string;
  teamId: string;
  username: string;
  teamName: string;
  teamLogo: string | null;
}

function buildManagers(standings: MyTeamData['standings']): Manager[] {
  const seen = new Map<string, Manager>();
  for (const s of standings) {
    if (!seen.has(s.owner_id)) {
      seen.set(s.owner_id, {
        ownerId: s.owner_id,
        teamId: s.team_id,
        username: s.owner_username,
        teamName: s.team_name,
        teamLogo: s.team_logo || null,
      });
    }
  }
  return [...seen.values()].sort((a, b) =>
    a.username.localeCompare(b.username),
  );
}

function MyTeamInner({
  promise,
  leagueId,
  platform,
}: {
  promise: Promise<MyTeamResult>;
  leagueId: string;
  platform: Platform;
}) {
  const result = use(promise);

  const managers = useMemo(
    () => (result.ok ? buildManagers(result.data.standings) : []),
    [result],
  );

  const [rawOwnerId, setRawOwnerId] = useState<string>(() =>
    getMyTeamOwnerId(leagueId),
  );

  // Resolve the effective selection during render so a stale/absent id falls back
  // to the first manager without an effect.
  const selectedOwnerId = managers.some((mgr) => mgr.ownerId === rawOwnerId)
    ? rawOwnerId
    : (managers[0]?.ownerId ?? '');
  const colorIndex = managers.findIndex(
    (mgr) => mgr.ownerId === selectedOwnerId,
  );

  // All hooks run before any early return (rules-of-hooks); the compute guards on
  // the loaded data being present and the selected manager resolving.
  const metrics = useMemo(() => {
    if (!result.ok) return null;
    const mgr = managers.find((m) => m.ownerId === selectedOwnerId);
    if (!mgr) return null;
    return computeTeamMetrics({
      teamId: mgr.teamId,
      platform,
      standings: result.data.standings,
      matchups: result.data.matchups,
      draftPicks: result.data.draftPicks,
      transactions: result.data.transactions,
      weekly: result.data.weekly,
    });
  }, [result, managers, selectedOwnerId, platform]);

  const insights = useMemo(
    () => (metrics ? computeInsights(metrics) : []),
    [metrics],
  );
  const verdict = useMemo(
    () => (metrics ? heroVerdict(metrics, insights) : ''),
    [metrics, insights],
  );

  const onSelect = (ownerId: string) => {
    setRawOwnerId(ownerId);
    setMyTeamOwnerId(leagueId, ownerId);
  };

  if (!result.ok) {
    return <ErrorAlert message={result.error} className="my-6" />;
  }
  if (managers.length === 0) {
    return (
      <p className="text-[13px] text-muted-foreground text-center py-12">
        No team data for this season yet.
      </p>
    );
  }

  return (
    <>
      <div className="flex items-center gap-2.5 mb-5">
        <label className="sr-only" htmlFor="my-team-select">
          Team
        </label>
        <select
          id="my-team-select"
          aria-label="Select team"
          value={selectedOwnerId}
          onChange={(e) => onSelect(e.target.value)}
          className="h-9 rounded-md border border-border bg-card px-3 text-[13px] font-medium"
        >
          {managers.map((mgr) => (
            <option key={mgr.ownerId} value={mgr.ownerId}>
              {mgr.username}
            </option>
          ))}
        </select>
      </div>

      {!metrics ? (
        <p className="text-[13px] text-muted-foreground text-center py-12">
          No data for this team this season.
        </p>
      ) : (
        <>
          <Hero m={metrics} color={avatarColor(colorIndex)} verdict={verdict} />
          <KpiRow m={metrics} />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6 items-start">
            <RecentForm m={metrics} />
            <StackUp m={metrics} />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6 items-start">
            <DraftReport m={metrics} />
            <TradeReport m={metrics} />
          </div>
          <Insights insights={insights} />
        </>
      )}
    </>
  );
}

function MyTeamSkeleton() {
  return (
    <div className="flex flex-col gap-6">
      <Skeleton className="h-24 w-full rounded-lg" />
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-20 rounded-lg" />
        ))}
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Skeleton className="h-56 rounded-lg" />
        <Skeleton className="h-56 rounded-lg" />
      </div>
    </div>
  );
}

export default function MyTeam() {
  const { leagueId, platform, seasons } = useMemo(() => getLeagueCookies(), []);

  const latestSeason = useMemo(
    () =>
      seasons.length > 0
        ? [...seasons].sort((a, b) => Number(b) - Number(a))[0]
        : '',
    [seasons],
  );
  const [season, setSeason] = useState(latestSeason);
  const effectiveSeason = season || latestSeason;

  const promise = useMemo(
    (): Promise<MyTeamResult> =>
      leagueId && effectiveSeason
        ? toResult(
            getMyTeamData(leagueId, platform, effectiveSeason),
            'Failed to load your team.',
          )
        : Promise.resolve({
            ok: true as const,
            data: {
              standings: [],
              matchups: [],
              draftPicks: [],
              transactions: [],
              weekly: new Map(),
            },
          }),
    [leagueId, platform, effectiveSeason],
  );

  return (
    <div className="flex flex-1 flex-col p-6 overflow-auto">
      <div className="max-w-225 mx-auto w-full">
        <div className="flex items-center justify-between gap-3 mb-6">
          <h1 className="text-2xl font-bold text-foreground">Report Card</h1>
          {seasons.length > 0 && (
            <SeasonSelect
              seasons={seasons}
              value={effectiveSeason}
              onValueChange={setSeason}
            />
          )}
        </div>
        <Suspense fallback={<MyTeamSkeleton />}>
          <MyTeamInner
            promise={promise}
            leagueId={leagueId}
            platform={platform}
          />
        </Suspense>
      </div>
    </div>
  );
}
