import { Skeleton } from '@/components/ui/skeleton';

export function SkeletonManagerHistory() {
  return (
    <div>
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center gap-3 mb-6">
        <div className="flex items-center gap-4 sm:flex-1 order-2 sm:order-1">
          <Skeleton className="w-14 h-14 rounded-full shrink-0" />
          <div className="flex-1">
            <Skeleton className="h-4 w-32" />
          </div>
        </div>
        <Skeleton className="h-9 w-full sm:w-36 rounded-md order-1 sm:order-2" />
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-2.5 mb-6">
        {Array.from({ length: 5 }).map((_, i) => (
          <div
            key={i}
            className="bg-card border border-border/50 rounded-lg p-3"
          >
            <Skeleton className="h-2.5 w-20 mb-2" />
            <Skeleton className="h-6 w-14 mb-1" />
            <Skeleton className="h-2.5 w-16" />
          </div>
        ))}
      </div>

      {/* Season finish chart */}
      <Skeleton className="h-3 w-28 mb-2.5" />
      <div className="bg-card border border-border/50 rounded-lg p-5 mb-6">
        <Skeleton className="w-full h-48" />
      </div>

      {/* Season cards */}
      <Skeleton className="h-3 w-36 mb-2.5" />
      <div className="flex flex-col gap-2.5 mb-6">
        {Array.from({ length: 3 }).map((_, i) => (
          <div
            key={i}
            className="bg-card border border-border/50 rounded-lg p-3.5 grid grid-cols-[80px_1fr_auto] gap-3 items-center"
          >
            <div className="flex flex-col gap-1.5">
              <Skeleton className="h-3.5 w-14" />
              <Skeleton className="h-2.5 w-20" />
              <Skeleton className="h-5 w-16 rounded-full" />
            </div>
            <div className="flex gap-5">
              {Array.from({ length: 4 }).map((_, j) => (
                <div key={j} className="flex flex-col gap-1">
                  <Skeleton className="h-2.5 w-10" />
                  <Skeleton className="h-3.5 w-12" />
                </div>
              ))}
            </div>
            <div className="flex flex-col items-end gap-1">
              <Skeleton className="h-6 w-10" />
              <Skeleton className="h-2.5 w-8" />
            </div>
          </div>
        ))}
      </div>

      {/* Rivalry cards */}
      <Skeleton className="h-3 w-16 mb-2.5" />
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <div
            key={i}
            className="bg-card border border-border/50 rounded-lg p-3.5 flex flex-col gap-2.5"
          >
            <div className="flex items-center gap-2.5">
              <Skeleton className="w-9 h-9 rounded-full shrink-0" />
              <div className="flex-1 flex flex-col gap-1">
                <Skeleton className="h-3 w-20" />
                <Skeleton className="h-2.5 w-16" />
              </div>
              <Skeleton className="h-5 w-16 rounded-full" />
            </div>
            <div className="flex flex-col gap-1.5">
              <Skeleton className="h-5 w-16" />
              <Skeleton className="h-1.5 w-full rounded-full" />
            </div>
            <div className="flex gap-4">
              {Array.from({ length: 4 }).map((_, j) => (
                <div key={j} className="flex flex-col gap-0.5">
                  <Skeleton className="h-2.5 w-10" />
                  <Skeleton className="h-3 w-10" />
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Season schedule panel ───────────────────────────────────────────────────
