import { AlertTriangle } from 'lucide-react';

import type { Platform } from '@/components/api/types';
import { Spinner } from '@/components/spinner';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';

export function Step4({
  currentSeasons,
  newPlatform,
  newPlatformLeagueId,
  newSeason,
  totalManagers,
  mappedManagers,
  isSubmitting,
  submitError,
  onConfirm,
  onBack,
}: {
  currentSeasons: string[];
  newPlatform: Platform;
  newPlatformLeagueId: string;
  newSeason?: string;
  totalManagers: number;
  mappedManagers: number;
  isSubmitting: boolean;
  submitError: string | null;
  onConfirm: () => void;
  onBack: () => void;
}) {
  const seasonRange =
    currentSeasons.length > 0
      ? `${currentSeasons[0]}–${currentSeasons[currentSeasons.length - 1]}`
      : '—';

  return (
    <div className="flex flex-col gap-5">
      <div>
        <p className="text-[13px] font-medium mb-1">Review migration</p>
        <p className="text-[12px] text-muted-foreground">
          Confirm the details below before starting the migration.
        </p>
      </div>

      <div className="bg-muted/50 rounded-lg p-4 flex flex-col gap-2.5">
        <div className="flex items-center justify-between">
          <span className="text-[12px] text-muted-foreground uppercase tracking-wide">
            Current seasons
          </span>
          <span className="text-[13px] font-medium">{seasonRange}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-[12px] text-muted-foreground uppercase tracking-wide">
            New platform
          </span>
          <span className="text-[13px] font-medium">{newPlatform}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-[12px] text-muted-foreground uppercase tracking-wide">
            New league ID
          </span>
          <span className="text-[13px]">{newPlatformLeagueId}</span>
        </div>
        {newSeason && (
          <div className="flex items-center justify-between">
            <span className="text-[12px] text-muted-foreground uppercase tracking-wide">
              New season
            </span>
            <span className="text-[13px] font-medium">{newSeason}</span>
          </div>
        )}
        <div className="flex items-center justify-between">
          <span className="text-[12px] text-muted-foreground uppercase tracking-wide">
            Managers mapped
          </span>
          <span className="text-[13px] font-medium">
            {mappedManagers} of {totalManagers}
          </span>
        </div>
      </div>

      <Alert variant="destructive">
        <AlertTriangle className="h-4 w-4" />
        <AlertDescription className="text-[12px]">
          This action cannot be undone. All-time metrics will be recalculated to
          reflect the merged history.
        </AlertDescription>
      </Alert>

      {submitError && <p className="text-sm text-destructive">{submitError}</p>}

      <div className="flex gap-2">
        <Button
          variant="outline"
          className="flex-1 cursor-pointer"
          onClick={onBack}
          disabled={isSubmitting}
        >
          Back
        </Button>
        <Button
          className="flex-1 cursor-pointer"
          onClick={onConfirm}
          disabled={isSubmitting}
        >
          {isSubmitting ? (
            <span className="flex items-center gap-2">
              <Spinner className="text-primary-foreground" />
              Starting migration…
            </span>
          ) : (
            'Confirm Migration'
          )}
        </Button>
      </div>
    </div>
  );
}
