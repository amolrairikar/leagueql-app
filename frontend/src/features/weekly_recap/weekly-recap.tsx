import { Suspense, use, useMemo } from 'react';

import { getSeasonMatchups, getWeekRecap, type RecapItem } from './api-calls';

import type { Platform } from '@/components/api/types';
import { Skeleton } from '@/components/ui/skeleton';
import { type Result, toResult } from '@/lib/result';

type RecapResult = Result<RecapItem | null>;

/** Resolve the latest week present in the season's matchups (default when none picked). */
function latestWeekFrom(matchups: { week: string }[]): number {
  const weeks = matchups
    .map((m) => Number(m.week))
    .filter((w) => !Number.isNaN(w));
  return weeks.length ? Math.max(...weeks) : 1;
}

function RecapInner({ promise }: { promise: Promise<RecapResult> }) {
  const result = use(promise);

  if (!result.ok) {
    return (
      <p className="text-[13px] text-muted-foreground text-center py-8">
        {result.error}
      </p>
    );
  }

  const recap = result.data;
  if (!recap) {
    return (
      <p className="text-[13px] text-muted-foreground text-center py-8">
        No recap for this week yet.
      </p>
    );
  }

  const paragraphs = recap.body.split('\n\n').filter((p) => p.trim());

  return (
    <div className="bg-card border border-border/50 rounded-lg p-6 flex flex-col gap-4">
      <h3 className="text-xl font-semibold text-foreground leading-snug">
        {recap.headline}
      </h3>
      <div className="flex flex-col gap-3">
        {paragraphs.map((paragraph, i) => (
          <p
            key={i}
            className="text-[14px] text-muted-foreground leading-relaxed"
          >
            {paragraph}
          </p>
        ))}
      </div>
    </div>
  );
}

function SkeletonRecap() {
  return (
    <div className="bg-card border border-border/50 rounded-lg p-6 flex flex-col gap-4">
      <Skeleton className="h-6 w-3/4" />
      <div className="flex flex-col gap-2.5">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-4 w-full" />
        ))}
        <Skeleton className="h-4 w-2/3" />
      </div>
    </div>
  );
}

export default function WeeklyRecap({
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
    (): Promise<RecapResult> =>
      leagueId && season
        ? toResult(
            // Resolve the active week (selected, else latest available) from the
            // cached season matchups, then fetch that week's cached recap.
            getSeasonMatchups(leagueId, platform, season).then((res) => {
              const activeWeek = selectedWeek ?? latestWeekFrom(res.data);
              return getWeekRecap(leagueId, platform, season, activeWeek).then(
                (recap) => recap.data[0] ?? null,
              );
            }),
            'Failed to load weekly recap.',
          )
        : Promise.resolve({ ok: true as const, data: null }),
    [leagueId, platform, season, selectedWeek],
  );

  return (
    <Suspense fallback={<SkeletonRecap />}>
      <RecapInner promise={promise} />
    </Suspense>
  );
}
