import { Suspense, use, useMemo, useState } from 'react';

import { getSeasonMatchups, type MatchupItem } from './api-calls';
import { BoxPlot } from './box-plot';
import { computeScoreDistribution } from './compute-score-distribution';

import type { Platform } from '@/components/api/types';
import { Skeleton } from '@/components/ui/skeleton';
import SeasonSelect from '@/features/season_select/season-select';
import { SubscriptionGuard } from '@/features/subscription/subscription-guard';
import { getLeagueCookies } from '@/lib/cookie-handler';
import { type Result, toResult } from '@/lib/result';

type MatchupsResult = Result<MatchupItem[]>;

function ScoreDistributionInner({
  promise,
}: {
  promise: Promise<MatchupsResult>;
}) {
  const result = use(promise);

  if (!result.ok) {
    return (
      <p className="text-[13px] text-muted-foreground text-center py-8">
        {result.error}
      </p>
    );
  }

  const data = computeScoreDistribution(result.data);

  if (data.teams.length === 0) {
    return (
      <p className="text-[13px] text-muted-foreground text-center py-8">
        No regular-season scores to chart for this season yet.
      </p>
    );
  }

  return <BoxPlot data={data} />;
}

function SkeletonChart() {
  return (
    <div className="p-3.5">
      <Skeleton className="w-full h-80" />
    </div>
  );
}

/**
 * Premium box-and-whisker chart of each manager's weekly scores for a season
 * (FE-033). Kept as its own component so the {@link SubscriptionGuard} can leave
 * it unmounted while locked — its `MATCHUPS` data is never fetched then.
 */
export function ScoreDistribution({
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
            'Failed to load score-distribution data.',
          )
        : Promise.resolve({ ok: true as const, data: [] }),
    [leagueId, platform, season],
  );

  return (
    <div className="bg-card border border-border/50 rounded-lg p-5 overflow-x-auto">
      <Suspense fallback={<SkeletonChart />}>
        <ScoreDistributionInner promise={promise} />
      </Suspense>
    </div>
  );
}

export default function Analytics() {
  const { leagueId, platform, seasons } = useMemo(() => getLeagueCookies(), []);

  const defaultSeason =
    [...seasons].sort((a, b) => Number(b) - Number(a))[0] ?? '';
  const [selectedSeason, setSelectedSeason] = useState(defaultSeason);

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
          Weekly score distribution
        </p>

        <SubscriptionGuard
          featureFlag="premium_feature"
          featureLabel="Analytics"
        >
          <ScoreDistribution
            leagueId={leagueId}
            platform={platform}
            season={selectedSeason}
          />
        </SubscriptionGuard>
      </div>
    </div>
  );
}
