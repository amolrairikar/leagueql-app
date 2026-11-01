import { AlertTriangle } from 'lucide-react';

import type { Platform } from '@/components/api/types';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';

export function Step1({
  leagueId,
  platform,
  seasons,
  leagueName,
  onNext,
}: {
  leagueId: string;
  platform: Platform;
  seasons: string[];
  leagueName: string;
  onNext: () => void;
}) {
  const seasonRange =
    seasons.length > 0
      ? seasons.length === 1
        ? seasons[0]
        : `${seasons[0]}–${seasons[seasons.length - 1]}`
      : '—';

  return (
    <div className="flex flex-col gap-5">
      <Alert className="border-amber-500/50 bg-amber-500/10">
        <AlertTriangle className="h-4 w-4 text-amber-500" />
        <AlertTitle className="text-amber-600 dark:text-amber-400">
          Experimental Feature
        </AlertTitle>
        <AlertDescription className="text-amber-700 dark:text-amber-300">
          League migration is an experimental feature. Please review each step
          carefully before confirming. This action cannot be undone — all-time
          metrics will be recalculated to reflect the merged history.
        </AlertDescription>
      </Alert>

      <div className="flex flex-col gap-3">
        <p className="text-[13px] text-muted-foreground">
          You are migrating the following league to a new platform:
        </p>
        <div className="bg-muted/50 rounded-lg p-4 flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <span className="text-[12px] text-muted-foreground uppercase tracking-wide">
              League
            </span>
            <span className="text-[13px] font-medium">{leagueName}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-[12px] text-muted-foreground uppercase tracking-wide">
              Current platform
            </span>
            <span className="text-[13px] font-medium">{platform}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-[12px] text-muted-foreground uppercase tracking-wide">
              League ID
            </span>
            <span className="text-[13px]">{leagueId}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-[12px] text-muted-foreground uppercase tracking-wide">
              Seasons
            </span>
            <span className="text-[13px] font-medium">{seasonRange}</span>
          </div>
        </div>
        <p className="text-[12px] text-muted-foreground">
          Your {platform} league data (seasons {seasonRange}) will be preserved
          after migration.
        </p>
      </div>

      <Button className="w-full cursor-pointer" onClick={onNext}>
        Continue
      </Button>
    </div>
  );
}
