import { Skeleton } from '@/components/ui/skeleton';

export function StatsSkeleton() {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 mb-6">
      {Array.from({ length: 4 }).map((_, i) => (
        <div
          key={i}
          className="bg-card border border-border/50 rounded-lg p-3 text-center"
        >
          <Skeleton className="h-3 w-20 mx-auto mb-2" />
          <Skeleton className="h-6 w-12 mx-auto mb-1" />
          <Skeleton className="h-3 w-16 mx-auto" />
        </div>
      ))}
    </div>
  );
}

export function ChampionsSkeleton() {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-1.5 mb-6">
      {Array.from({ length: 8 }).map((_, i) => (
        <div
          key={i}
          className="bg-card border border-border/50 rounded-lg p-2.5 flex flex-col gap-0.5"
        >
          <Skeleton className="h-3 w-8 mb-1" />
          <Skeleton className="h-4 w-full mb-0.5" />
          <Skeleton className="h-3 w-16 mb-0.5" />
          <Skeleton className="h-3 w-20" />
        </div>
      ))}
    </div>
  );
}

export function AllTimeStandingsSkeleton() {
  return (
    <div className="mb-6">
      <div className="flex items-center justify-between mb-2.5">
        <Skeleton className="h-3 w-32" />
        <Skeleton className="h-5 w-44" />
      </div>
      <div className="bg-card border border-border/50 rounded-lg overflow-hidden">
        {Array.from({ length: 8 }).map((_, i) => (
          <div
            key={i}
            className="flex items-center gap-2 px-3.5 py-2.5 border-b border-border/50 last:border-0"
          >
            <Skeleton className="w-7 h-7 rounded-full shrink-0" />
            <Skeleton className="h-3 w-32" />
            <Skeleton className="h-3 w-16 ml-auto" />
          </div>
        ))}
      </div>
    </div>
  );
}

// Stacked skeletons matching the summary layout, shown while the single data
// call resolves.
export function SummarySkeleton() {
  return (
    <>
      <StatsSkeleton />
      <p className="text-[11px] font-medium uppercase tracking-[0.08em] text-muted-foreground mb-2.5">
        Champions
      </p>
      <ChampionsSkeleton />
      <AllTimeStandingsSkeleton />
      <p className="text-[11px] font-medium uppercase tracking-[0.08em] text-muted-foreground mb-2.5">
        Final Standings Position by Season
      </p>
      <Skeleton className="h-56 w-full" />
    </>
  );
}
