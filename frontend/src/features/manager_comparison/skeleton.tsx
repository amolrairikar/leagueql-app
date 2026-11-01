import { Fragment } from 'react';

import { Skeleton } from '@/components/ui/skeleton';
import { STAT_DEFS } from '@/features/manager_comparison/stat-defs';

export function ManagerComparisonSkeleton() {
  return (
    <div className="flex flex-1 flex-col p-6 overflow-auto">
      <div className="max-w-275 mx-auto w-full">
        <div className="grid grid-cols-1 sm:grid-cols-[minmax(0,1fr)_minmax(0,275px)] gap-4 items-stretch">
          <div className="flex flex-col gap-3">
            {/* Selector row */}
            <div className="grid grid-cols-[1fr_56px_1fr] items-center">
              <Skeleton className="h-9 w-full" />
              <Skeleton className="w-8.5 h-8.5 rounded-full mx-auto" />
              <Skeleton className="h-9 w-full" />
            </div>
            {/* Comparison grid */}
            <div className="grid grid-cols-[1fr_110px_1fr]">
              {/* Avatar header row */}
              <div className="flex flex-col items-center gap-1.5 pb-4.5 pt-2.5">
                <Skeleton className="w-14 h-14 rounded-full" />
                <Skeleton className="h-3 w-20 mt-0.5" />
              </div>
              <div />
              <div className="flex flex-col items-center gap-1.5 pb-4.5 pt-2.5">
                <Skeleton className="w-14 h-14 rounded-full" />
                <Skeleton className="h-3 w-20 mt-0.5" />
              </div>
              {/* Stat rows */}
              {STAT_DEFS.map((s) => (
                <Fragment key={s.key}>
                  <div className="h-13 flex flex-col justify-center gap-1.25 px-2">
                    <Skeleton className="h-4 w-12" />
                    <Skeleton className="h-2 w-full" />
                  </div>
                  <div className="h-13 flex items-center justify-center">
                    <Skeleton className="h-3 w-14" />
                  </div>
                  <div className="h-13 flex flex-col justify-center gap-1.25 px-2 items-end">
                    <Skeleton className="h-4 w-12" />
                    <Skeleton className="h-2 w-full" />
                  </div>
                </Fragment>
              ))}
            </div>
          </div>
          {/* Game log panel */}
          <Skeleton className="h-96 sm:h-auto w-full rounded-lg" />
        </div>
      </div>
    </div>
  );
}
