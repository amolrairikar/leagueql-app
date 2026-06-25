import { Check, Copy } from 'lucide-react';
import { Suspense, use, useMemo, useState } from 'react';

import { getSeasonMatchups, getWeekRecap, type RecapItem } from './api-calls';

import type { Platform } from '@/components/api/types';
import { Button } from '@/components/ui/button';
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
        Weekly recap generating! Check back soon.
      </p>
    );
  }

  const paragraphs = recap.body.split('\n\n').filter((p) => p.trim());

  return (
    <div className="bg-card border border-border/50 rounded-lg p-6 flex flex-col gap-4">
      <div className="flex items-start justify-between gap-4">
        <h3 className="text-xl font-semibold text-foreground leading-snug">
          {recap.headline}
        </h3>
        <CopyRecapButton recap={recap} />
      </div>
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

/** Copies the recap (headline + body) to the clipboard, swapping to a check
 * mark for ~2s so the user knows the text is ready to paste into a group chat. */
function CopyRecapButton({ recap }: { recap: RecapItem }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    void navigator.clipboard
      ?.writeText(`${recap.headline}\n\n${recap.body}`)
      .then(() => {
        setCopied(true);
        setTimeout(() => {
          setCopied(false);
        }, 2000);
      });
  };

  return (
    <Button
      type="button"
      variant="ghost"
      size="icon"
      className="h-8 w-8 shrink-0 cursor-pointer text-muted-foreground"
      onClick={handleCopy}
      aria-label={copied ? 'Recap copied' : 'Copy recap'}
    >
      {copied ? (
        <Check className="size-4 text-green-600" />
      ) : (
        <Copy className="size-4" />
      )}
    </Button>
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
