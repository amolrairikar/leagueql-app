import { Suspense, use, useMemo } from 'react';

import { getLeague } from '@/components/api/leagues';
import { type AllTimeStandingsData } from '@/features/home_page/all-time-data';
import { LeagueSummary } from '@/features/home_page/league-summary';
import { SummarySkeleton } from '@/features/home_page/skeletons';
import { getManagerHistoryData } from '@/features/manager_history/api-calls';
import { getLeagueCookies } from '@/lib/cookie-handler';
import { toResult, type Result } from '@/lib/result';

function LeagueNameHeader({
  promise,
}: {
  promise: Promise<string | undefined>;
}) {
  const leagueName = use(promise);
  return (
    <div className="mb-6">
      <h1 className="text-2xl font-bold text-foreground">
        {leagueName ?? 'League Name'}
      </h1>
    </div>
  );
}

export default function HomePage() {
  const { leagueId, platform, seasons } = useMemo(() => getLeagueCookies(), []);

  const leagueNamePromise = useMemo(
    (): Promise<string | undefined> =>
      leagueId
        ? getLeague(leagueId, platform).then((res) => res.data.league_name)
        : Promise.resolve(undefined),
    [leagueId, platform],
  );

  const stats = useMemo(() => {
    if (seasons.length > 0) {
      const sortedSeasons = seasons.sort();
      const firstSeason = sortedSeasons[0];
      const lastSeason = sortedSeasons[sortedSeasons.length - 1];

      return [
        {
          label: 'Seasons played',
          value: String(seasons.length),
          sub: `${firstSeason} – ${lastSeason}`,
        },
      ];
    }
    return [];
  }, [seasons]);

  // Single API call for all data (getManagerHistoryData already uses optimized
  // single queries). Wrapped in toResult so a failure surfaces inline via
  // LeagueSummary instead of rejecting / showing empty tables.
  const dataResultPromise = useMemo(
    (): Promise<Result<AllTimeStandingsData>> =>
      leagueId && seasons.length > 0
        ? toResult(
            getManagerHistoryData(leagueId, platform, seasons),
            'Failed to load league data.',
          )
        : Promise.resolve({
            ok: true as const,
            data: { standings: [], matchups: [], migrationMapping: new Map() },
          }),
    [leagueId, platform, seasons],
  );

  return (
    <div className="flex flex-1 flex-col p-6 overflow-auto">
      <div className="max-w-225 mx-auto w-full">
        {/* Header */}
        <Suspense
          fallback={
            <div className="mb-6">
              <h1 className="text-2xl font-bold text-foreground">
                League Name
              </h1>
            </div>
          }
        >
          <LeagueNameHeader promise={leagueNamePromise} />
        </Suspense>

        {/* Stats, champions, all-time standings and chart all derive from one call */}
        <Suspense fallback={<SummarySkeleton />}>
          <LeagueSummary
            promise={dataResultPromise}
            stats={stats}
            seasons={seasons}
          />
        </Suspense>
      </div>
    </div>
  );
}
