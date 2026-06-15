import { Suspense, use, useMemo, type CSSProperties } from 'react';

import { getSeasonMatchups, type MatchupItem } from './api-calls';
import {
  computeScheduleSwap,
  formatRecord,
  type ScheduleSwapData,
} from './compute-schedule-swap';

import type { Platform } from '@/components/api/types';
import { TeamAvatar } from '@/components/team-avatar';
import { Skeleton } from '@/components/ui/skeleton';
import { avatarColor } from '@/lib/color-constants';
import { type Result, toResult } from '@/lib/result';

type MatchupsResult = Result<MatchupItem[]>;

/** Background tint for an off-diagonal cell, scaled by win delta vs. actual. */
function cellStyle(delta: number, maxAbs: number): CSSProperties {
  if (delta === 0 || maxAbs === 0) return {};
  const alpha = 0.12 + 0.22 * (Math.abs(delta) / maxAbs);
  const rgb = delta > 0 ? '34, 197, 94' : '239, 68, 68';
  return { backgroundColor: `rgba(${rgb}, ${alpha})` };
}

function Matrix({ data }: { data: ScheduleSwapData }) {
  const { teams, matrix } = data;

  const maxAbs = useMemo(() => {
    let max = 0;
    for (const row of teams) {
      for (const col of teams) {
        if (col.teamId === row.teamId) continue;
        const wins = matrix.get(row.teamId)!.get(col.teamId)!.wins;
        max = Math.max(max, Math.abs(wins - row.actual.wins));
      }
    }
    return max;
  }, [teams, matrix]);

  return (
    <div className="max-h-[70vh] overflow-auto">
      <table
        className="border-separate border-spacing-0 text-[12px]"
        style={{ minWidth: '100%' }}
      >
        <thead className="sticky top-0 z-20">
          <tr>
            <th className="sticky left-0 z-30 bg-muted border-b border-r border-border/50 px-3 py-2 text-left text-[10px] font-medium uppercase tracking-[0.06em] text-muted-foreground whitespace-nowrap">
              Team ╲ Schedule
            </th>
            {teams.map((col, i) => (
              <th
                key={col.teamId}
                className="bg-muted border-b border-border/50 px-2 py-2 align-bottom"
                title={col.ownerUsername}
              >
                <div className="flex flex-col items-center gap-1 w-14 mx-auto">
                  <TeamAvatar
                    teamLogo={col.teamLogo}
                    teamName={col.teamName}
                    ownerUsername={col.ownerUsername}
                    color={avatarColor(i)}
                  />
                  <span className="text-[10px] font-medium text-foreground truncate max-w-14 w-full text-center">
                    {col.ownerUsername}
                  </span>
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {teams.map((row, i) => (
            <tr key={row.teamId}>
              <td className="sticky left-0 z-10 bg-card border-b border-r border-border/50 px-3 py-2">
                <div className="flex items-center gap-2 w-44">
                  <TeamAvatar
                    teamLogo={row.teamLogo}
                    teamName={row.teamName}
                    ownerUsername={row.ownerUsername}
                    color={avatarColor(i)}
                  />
                  <div className="flex flex-col min-w-0">
                    <span className="text-[12px] font-medium text-foreground truncate">
                      {row.ownerUsername}
                    </span>
                    <span className="text-[10px] text-muted-foreground">
                      Actual {formatRecord(row.actual)}
                    </span>
                  </div>
                </div>
              </td>
              {teams.map((col) => {
                const rec = matrix.get(row.teamId)!.get(col.teamId)!;
                const isDiagonal = col.teamId === row.teamId;
                const delta = rec.wins - row.actual.wins;
                const title = isDiagonal
                  ? `${row.ownerUsername} — actual record ${formatRecord(rec)}`
                  : `${row.ownerUsername} with ${col.ownerUsername}'s schedule: ${formatRecord(
                      rec,
                    )} (${delta >= 0 ? '+' : ''}${delta} wins)`;
                return (
                  <td
                    key={col.teamId}
                    title={title}
                    style={isDiagonal ? undefined : cellStyle(delta, maxAbs)}
                    className={`border-b border-border/50 px-2 py-2 text-center tabular-nums ${
                      isDiagonal
                        ? 'bg-muted font-semibold text-foreground ring-1 ring-inset ring-border'
                        : 'text-foreground'
                    }`}
                  >
                    {rec.wins}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ScheduleSwapInner({ promise }: { promise: Promise<MatchupsResult> }) {
  const result = use(promise);

  if (!result.ok) {
    return (
      <p className="text-[13px] text-muted-foreground text-center py-8">
        {result.error}
      </p>
    );
  }

  const data = computeScheduleSwap(result.data);

  if (data.teams.length < 2) {
    return (
      <p className="text-[13px] text-muted-foreground text-center py-8">
        Not enough regular-season data to simulate schedule swaps for this
        season.
      </p>
    );
  }

  return <Matrix data={data} />;
}

function SkeletonMatrix() {
  return (
    <div className="p-3.5">
      <Skeleton className="w-full h-80" />
    </div>
  );
}

export default function ScheduleSwap({
  leagueId,
  platform,
  season,
}: {
  leagueId: string;
  platform: Platform;
  season: string;
}) {
  const promise = useMemo(
    (): Promise<MatchupsResult> =>
      leagueId && season
        ? toResult(
            getSeasonMatchups(leagueId, platform, season).then(
              (res) => res.data,
            ),
            'Failed to load schedule-swap data.',
          )
        : Promise.resolve({ ok: true as const, data: [] }),
    [leagueId, platform, season],
  );

  return (
    <div className="bg-card border border-border/50 rounded-lg overflow-hidden">
      <Suspense fallback={<SkeletonMatrix />}>
        <ScheduleSwapInner promise={promise} />
      </Suspense>
    </div>
  );
}
