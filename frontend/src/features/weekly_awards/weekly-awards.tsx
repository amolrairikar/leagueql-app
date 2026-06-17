import {
  Flame,
  Gauge,
  HeartCrack,
  Snowflake,
  ThumbsDown,
  Zap,
  type LucideIcon,
} from 'lucide-react';
import { Suspense, use, useMemo } from 'react';

import { getSeasonMatchups, type MatchupItem } from './api-calls';
import {
  AWARD_DEFS,
  computeWeeklyAwards,
  type AwardDef,
  type AwardKey,
  type AwardWinner,
  type StreakHolder,
  type TallyRow,
} from './compute-awards';

import type { Platform } from '@/components/api/types';
import { TeamAvatar } from '@/components/team-avatar';
import { Skeleton } from '@/components/ui/skeleton';
import { avatarColor, POSITION_COLORS } from '@/lib/color-constants';
import { type Result, toResult } from '@/lib/result';

type MatchupsResult = Result<MatchupItem[]>;

/** Icon + color tile for each award card, keyed by award type. */
const AWARD_STYLE: Record<
  AwardKey,
  { icon: LucideIcon; color: string; bg: string }
> = {
  highest: {
    icon: Flame,
    color: POSITION_COLORS.WR.color,
    bg: POSITION_COLORS.WR.bg,
  },
  lowest: {
    icon: Snowflake,
    color: POSITION_COLORS.DEF.color,
    bg: POSITION_COLORS.DEF.bg,
  },
  blowout: {
    icon: Zap,
    color: POSITION_COLORS.QB.color,
    bg: POSITION_COLORS.QB.bg,
  },
  narrowest: {
    icon: Gauge,
    color: POSITION_COLORS.RB.color,
    bg: POSITION_COLORS.RB.bg,
  },
  bestLoss: {
    icon: HeartCrack,
    color: POSITION_COLORS.TE.color,
    bg: POSITION_COLORS.TE.bg,
  },
  worstWin: {
    icon: ThumbsDown,
    color: POSITION_COLORS.K.color,
    bg: POSITION_COLORS.K.bg,
  },
};

function AwardCard({
  award,
  winner,
}: {
  award: AwardDef;
  winner: AwardWinner | undefined;
}) {
  const style = AWARD_STYLE[award.key];
  const Icon = style.icon;
  return (
    <div className="bg-card border border-border/50 rounded-lg p-4 flex flex-col gap-2.5">
      <div className="flex items-center gap-2.5">
        <div
          className="w-9 h-9 rounded-md flex items-center justify-center shrink-0"
          style={{ background: style.bg }}
        >
          <Icon size={18} stroke={style.color} strokeWidth={1.5} />
        </div>
        <span
          className="text-[11px] font-medium uppercase tracking-[0.07em]"
          style={{ color: style.color }}
        >
          {award.label}
        </span>
      </div>
      <div>
        {winner ? (
          <>
            <div className="text-[15px] font-medium text-foreground">
              {winner.ownerUsername}
            </div>
            <div className="text-[12px] text-muted-foreground">
              {winner.teamName || `Team ${winner.ownerUsername}`}
            </div>
            <div
              className="text-[11px] font-medium mt-0.5"
              style={{ color: style.color }}
            >
              {winner.statText}
            </div>
          </>
        ) : (
          <>
            <div className="text-[15px] font-medium text-foreground">—</div>
            <div className="text-[12px] text-muted-foreground">
              No award this week
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function TallyTable({
  tally,
  longestStreak,
}: {
  tally: TallyRow[];
  longestStreak: StreakHolder | null;
}) {
  const colorMap = useMemo(
    () => new Map(tally.map((r, i) => [r.teamId, avatarColor(i)])),
    [tally],
  );

  return (
    <div className="bg-card border border-border/50 rounded-lg overflow-hidden">
      <div className="max-h-[70vh] overflow-auto">
        <table
          className="border-separate border-spacing-0 text-[12px]"
          style={{ minWidth: '100%' }}
        >
          <thead className="sticky top-0 z-20">
            <tr>
              <th className="sticky left-0 z-30 bg-muted border-b border-r border-border/50 px-3 py-2 text-left text-[10px] font-medium uppercase tracking-[0.06em] text-muted-foreground whitespace-nowrap">
                Manager
              </th>
              {AWARD_DEFS.map((d) => (
                <th
                  key={d.key}
                  title={d.short}
                  className="bg-muted border-b border-border/50 px-2 py-2 text-center text-[10px] font-medium uppercase tracking-[0.06em] text-muted-foreground whitespace-nowrap"
                >
                  {d.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {tally.map((row) => (
              <tr key={row.teamId}>
                <td className="sticky left-0 z-10 bg-card border-b border-r border-border/50 px-3 py-2">
                  <div className="flex items-center gap-2 w-44">
                    <TeamAvatar
                      teamLogo={row.teamLogo}
                      teamName={row.teamName}
                      ownerUsername={row.ownerUsername}
                      color={colorMap.get(row.teamId)!}
                    />
                    <div className="flex flex-col min-w-0">
                      <span className="text-[12px] font-medium text-foreground truncate">
                        {row.ownerUsername}
                      </span>
                      <span className="text-[10px] text-muted-foreground truncate">
                        {row.teamName || `Team ${row.ownerUsername}`}
                      </span>
                    </div>
                  </div>
                </td>
                {AWARD_DEFS.map((d) => (
                  <td
                    key={d.key}
                    className="border-b border-border/50 px-2 py-2 text-center tabular-nums"
                  >
                    {row.counts[d.key] > 0 ? (
                      <span className="text-foreground">
                        {row.counts[d.key]}
                      </span>
                    ) : (
                      <span className="text-muted-foreground">0</span>
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {longestStreak && (
        <div className="border-t border-border/50 px-3.5 py-2.5 text-[12px] text-muted-foreground">
          <Flame
            className="inline-block w-3.5 h-3.5 mr-1 -mt-0.5"
            stroke={POSITION_COLORS.WR.color}
            strokeWidth={1.5}
          />
          Longest active win streak:{' '}
          <span className="font-medium text-foreground">
            {longestStreak.ownerUsername}
          </span>{' '}
          (W{longestStreak.length})
        </div>
      )}
    </div>
  );
}

function WeeklyAwardsInner({
  promise,
  selectedWeek,
}: {
  promise: Promise<MatchupsResult>;
  selectedWeek: number | null;
}) {
  const result = use(promise);

  if (!result.ok) {
    return (
      <p className="text-[13px] text-muted-foreground text-center py-8">
        {result.error}
      </p>
    );
  }

  const data = computeWeeklyAwards(result.data, selectedWeek);

  if (data.tally.length === 0) {
    return (
      <p className="text-[13px] text-muted-foreground text-center py-8">
        Not enough matchup data for awards this season.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {AWARD_DEFS.map((d) => (
          <AwardCard key={d.key} award={d} winner={data.awards[d.key]} />
        ))}
      </div>
      <TallyTable tally={data.tally} longestStreak={data.longestStreak} />
    </div>
  );
}

function SkeletonAwards() {
  return (
    <div className="flex flex-col gap-6">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {Array.from({ length: 6 }).map((_, i) => (
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
      <Skeleton className="w-full h-64" />
    </div>
  );
}

export default function WeeklyAwards({
  leagueId,
  platform,
  season,
  selectedWeek,
}: {
  leagueId: string;
  platform: Platform;
  season: string;
  selectedWeek: number | null;
}) {
  const promise = useMemo(
    (): Promise<MatchupsResult> =>
      leagueId && season
        ? toResult(
            getSeasonMatchups(leagueId, platform, season).then(
              (res) => res.data,
            ),
            'Failed to load weekly awards.',
          )
        : Promise.resolve({ ok: true as const, data: [] }),
    [leagueId, platform, season],
  );

  return (
    <Suspense fallback={<SkeletonAwards />}>
      <WeeklyAwardsInner promise={promise} selectedWeek={selectedWeek} />
    </Suspense>
  );
}
