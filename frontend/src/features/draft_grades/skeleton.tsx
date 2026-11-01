import { Skeleton } from '@/components/ui/skeleton';

export function DraftGradesSkeleton() {
  return (
    <div className="w-full max-w-250">
      <div className="flex items-center gap-2.5 mb-6">
        <Skeleton className="h-8 w-20" />
        <Skeleton className="h-8 w-24" />
        <Skeleton className="h-8 w-24 ml-2" />
        <Skeleton className="h-8 w-36" />
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 mb-6">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-20 rounded-lg" />
        ))}
      </div>
      <Skeleton className="h-64 rounded-lg" />
    </div>
  );
}

// ── Content ───────────────────────────────────────────────────────────────────
