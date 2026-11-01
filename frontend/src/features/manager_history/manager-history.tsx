import { Suspense, use, useMemo, useState } from 'react';

import { AllTimeStatCards } from '@/features/manager_history/all-time-stat-cards';
import { getManagerHistoryData } from '@/features/manager_history/api-calls';
import { ManagerHeader } from '@/features/manager_history/manager-header';
import { processData } from '@/features/manager_history/process-data';
import { RivalriesSection } from '@/features/manager_history/rivalries-section';
import { SeasonBySeason } from '@/features/manager_history/season-by-season';
import { SeasonFinishChart } from '@/features/manager_history/season-finish-chart';
import { SkeletonManagerHistory } from '@/features/manager_history/skeleton';
import { type DataResult } from '@/features/manager_history/types';
import { getLeagueCookies, type Platform } from '@/lib/cookie-handler';
import { toResult } from '@/lib/result';

function ManagerHistoryContent({
  promise,
  platform,
}: {
  promise: Promise<DataResult>;
  platform: Platform;
}) {
  const result = use(promise);
  const [selectedManagerIndex, setSelectedManagerIndex] = useState(0);

  if (!result.ok) {
    return (
      <div className="text-center py-8 text-[13px] text-destructive">
        {result.error}
      </div>
    );
  }

  const managers = result.data;
  if (managers.length === 0) {
    return (
      <div className="text-center py-8 text-[13px] text-muted-foreground">
        No manager data available.
      </div>
    );
  }

  const idx = Math.min(selectedManagerIndex, managers.length - 1);
  const m = managers[idx];

  return (
    <div>
      <ManagerHeader
        managers={managers}
        idx={idx}
        m={m}
        onSelect={setSelectedManagerIndex}
      />

      <AllTimeStatCards m={m} />

      <SeasonFinishChart m={m} />

      <SeasonBySeason m={m} platform={platform} />

      <RivalriesSection m={m} />
    </div>
  );
}

export default function ManagerHistory() {
  const { leagueId, platform, seasons } = useMemo(() => getLeagueCookies(), []);

  const dataPromise = useMemo(
    (): Promise<DataResult> =>
      leagueId && seasons.length > 0
        ? toResult(
            getManagerHistoryData(leagueId, platform, seasons).then(
              ({ standings, matchups, migrationMapping }) =>
                processData(standings, matchups, migrationMapping),
            ),
            'Failed to load manager data.',
          )
        : Promise.resolve({ ok: true as const, data: [] }),
    [leagueId, platform, seasons],
  );

  return (
    <div className="flex flex-1 flex-col p-6 overflow-auto">
      <div className="max-w-225 mx-auto w-full">
        <Suspense fallback={<SkeletonManagerHistory />}>
          <ManagerHistoryContent promise={dataPromise} platform={platform} />
        </Suspense>
      </div>
    </div>
  );
}
