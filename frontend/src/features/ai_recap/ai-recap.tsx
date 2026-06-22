import { Newspaper } from 'lucide-react';
import { Suspense, use, useMemo } from 'react';

import { getWeekRecap, type RecapItem } from './api-calls';

import type { Platform } from '@/components/api/types';
import { Skeleton } from '@/components/ui/skeleton';
import { ErrorAlert } from '@/lib/error-alert';
import { type Result, toResult } from '@/lib/result';

type RecapResult = Result<RecapItem | null>;

function EmptyState() {
  return (
    <div className="bg-card border border-border/50 rounded-lg p-6 text-center">
      <Newspaper
        className="mx-auto mb-2 w-5 h-5 text-muted-foreground"
        strokeWidth={1.5}
      />
      <p className="text-[13px] text-muted-foreground">
        No recap for this week yet. Recaps are generated automatically — check
        back shortly.
      </p>
    </div>
  );
}

function AiRecapInner({ promise }: { promise: Promise<RecapResult> }) {
  const result = use(promise);

  if (!result.ok) {
    return <ErrorAlert message={result.error} />;
  }

  const recap = result.data;
  if (!recap) {
    return <EmptyState />;
  }

  return (
    <div className="bg-card border border-border/50 rounded-lg p-5 flex flex-col gap-3">
      <div className="flex items-center gap-2.5">
        <div className="w-9 h-9 rounded-md bg-muted flex items-center justify-center shrink-0">
          <Newspaper size={18} strokeWidth={1.5} className="text-foreground" />
        </div>
        <h3 className="text-[16px] font-medium text-foreground leading-snug">
          {recap.headline}
        </h3>
      </div>
      <div className="text-[13px] leading-relaxed text-foreground/90 whitespace-pre-line">
        {recap.body}
      </div>
    </div>
  );
}

function SkeletonRecap() {
  return (
    <div className="bg-card border border-border/50 rounded-lg p-5 flex flex-col gap-3">
      <div className="flex items-center gap-2.5">
        <Skeleton className="w-9 h-9 rounded-md shrink-0" />
        <Skeleton className="h-5 w-64" />
      </div>
      <div className="flex flex-col gap-2">
        <Skeleton className="h-3 w-full" />
        <Skeleton className="h-3 w-full" />
        <Skeleton className="h-3 w-3/4" />
      </div>
    </div>
  );
}

/**
 * AI weekly recap section for the matchups page (FE-033). Fetches and renders the
 * stored recap for the selected season/week; empty state when none exists yet,
 * inline error on failure. Mirrors the `<WeeklyAwards>` premium-gated display.
 */
export default function AiRecap({
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
      leagueId && season && selectedWeek != null
        ? toResult(
            getWeekRecap(leagueId, platform, season, selectedWeek),
            'Failed to load the weekly recap.',
          )
        : Promise.resolve({ ok: true as const, data: null }),
    [leagueId, platform, season, selectedWeek],
  );

  return (
    <Suspense fallback={<SkeletonRecap />}>
      <AiRecapInner promise={promise} />
    </Suspense>
  );
}
