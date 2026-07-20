import { Info } from 'lucide-react';
import { Suspense, use, useMemo, useState } from 'react';

import { getSeasonMatchups, type MatchupItem } from './api-calls';
import { computePositionalScoring } from './compute-positional-scoring';
import { computePowerRankings } from './compute-power-rankings';
import { computeScoreDistribution } from './compute-score-distribution';
import { JoyPlot } from './joy-plot';
import { PositionalScoringChart } from './positional-scoring-chart';
import { PowerRankingsChart } from './power-rankings-chart';

import type { Platform } from '@/components/api/types';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import SeasonSelect from '@/features/season_select/season-select';
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

  return <JoyPlot data={data} />;
}

function SkeletonChart() {
  return (
    <div className="p-3.5">
      <Skeleton className="w-full h-80" />
    </div>
  );
}

function PowerRankingsInner({ promise }: { promise: Promise<MatchupsResult> }) {
  const result = use(promise);

  if (!result.ok) {
    return (
      <p className="text-[13px] text-muted-foreground text-center py-8">
        {result.error}
      </p>
    );
  }

  const data = computePowerRankings(result.data);

  // An all-play power score needs at least one opponent, so a lone manager (or
  // no data) has nothing to chart.
  if (data.teams.length < 2) {
    return (
      <p className="text-[13px] text-muted-foreground text-center py-8">
        Not enough regular-season games to rank teams for this season yet.
      </p>
    );
  }

  return <PowerRankingsChart data={data} />;
}

/**
 * Multi-line power-rankings trend chart for a season (FE-033). Its own component,
 * mirroring {@link ScoreDistribution}, so each chart fetches its `MATCHUPS` data
 * independently.
 */
export function PowerRankings({
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
            'Failed to load power-rankings data.',
          )
        : Promise.resolve({ ok: true as const, data: [] }),
    [leagueId, platform, season],
  );

  return (
    <div className="bg-card border border-border/50 rounded-lg p-5 overflow-x-auto">
      <Suspense fallback={<SkeletonChart />}>
        <PowerRankingsInner promise={promise} />
      </Suspense>
    </div>
  );
}

function PositionalScoringInner({
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

  const data = computePositionalScoring(result.data);

  if (data.teams.length === 0) {
    return (
      <p className="text-[13px] text-muted-foreground text-center py-8">
        No starter scoring to chart for this season yet.
      </p>
    );
  }

  return <PositionalScoringChart data={data} />;
}

/**
 * Stacked-bar chart of each manager's season starter points split by position
 * (FE-033). Like {@link PowerRankings} it is its own component so each chart
 * fetches its `MATCHUPS` data independently.
 */
export function PositionalScoring({
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
            'Failed to load positional-scoring data.',
          )
        : Promise.resolve({ ok: true as const, data: [] }),
    [leagueId, platform, season],
  );

  return (
    <div className="bg-card border border-border/50 rounded-lg p-5 overflow-x-auto">
      <Suspense fallback={<SkeletonChart />}>
        <PositionalScoringInner promise={promise} />
      </Suspense>
    </div>
  );
}

/**
 * Ridgeline (joy) chart of each manager's weekly scores for a season (FE-033).
 * Kept as its own component so each chart fetches its `MATCHUPS` data
 * independently.
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

        <ScoreDistribution
          leagueId={leagueId}
          platform={platform}
          season={selectedSeason}
        />

        <div className="mb-2.5 mt-8">
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <span className="inline-flex items-center gap-1 cursor-default text-[11px] font-medium uppercase tracking-[0.08em] text-muted-foreground">
                  Power Rankings
                  <Info className="w-3 h-3 shrink-0" />
                </span>
              </TooltipTrigger>
              <TooltipContent
                side="top"
                className="max-w-80 text-left leading-relaxed bg-popover text-popover-foreground border border-border shadow-md [&>svg]:fill-popover [&>svg]:bg-popover"
              >
                Each week, teams are ranked by a power score that blends how
                often you&apos;d beat the rest of the league (50%), how much you
                score (30%), and how hot you&apos;ve been lately (20%).
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>

        <PowerRankings
          leagueId={leagueId}
          platform={platform}
          season={selectedSeason}
        />

        <p className="text-[11px] font-medium uppercase tracking-[0.08em] text-muted-foreground mb-2.5 mt-8">
          Positional Scoring
        </p>

        <PositionalScoring
          leagueId={leagueId}
          platform={platform}
          season={selectedSeason}
        />
      </div>
    </div>
  );
}
