import { Bell } from 'lucide-react';
import { useState } from 'react';

import { formatSeasons, useLineupBackfill } from './use-lineup-backfill';

/**
 * Header notification bell for a Yahoo league whose weekly player scores are
 * still being backfilled or couldn't be loaded yet (frontend/lineup-data-status).
 * Hidden when nothing is pending/failed (and in demo mode / with no league, via
 * the hook's bypass). Opening it explains which seasons are affected.
 */
export function LineupBackfillBell() {
  const { pendingSeasons, failedSeasons } = useLineupBackfill();
  const [open, setOpen] = useState(false);

  if (pendingSeasons.length === 0 && failedSeasons.length === 0) return null;

  return (
    <div className="relative ml-1">
      <button
        type="button"
        aria-label="Player score notifications"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        className="relative p-2 rounded-md hover:bg-muted transition-colors cursor-pointer"
      >
        <Bell className="size-4 text-foreground" aria-hidden="true" />
        <span
          data-testid="lineup-bell-indicator"
          className="absolute top-1.5 right-1.5 size-2 rounded-full bg-primary"
        />
      </button>
      {open && (
        <div
          role="status"
          className="absolute right-0 top-full mt-2 w-72 z-50 rounded-lg border border-border/50 bg-card p-3 text-[12px] text-foreground shadow-md space-y-2"
        >
          {pendingSeasons.length > 0 && (
            <p>
              Player box scores for {formatSeasons(pendingSeasons)} are still
              loading. Team scores, standings, and records are already complete.
            </p>
          )}
          {failedSeasons.length > 0 && (
            <p className="text-muted-foreground">
              Couldn&apos;t load player scores for{' '}
              {formatSeasons(failedSeasons)} yet. We&apos;ll retry
              automatically.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
