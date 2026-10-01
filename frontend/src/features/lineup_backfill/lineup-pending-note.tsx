import { Hourglass } from 'lucide-react';

import { formatSeasons } from './use-lineup-backfill';

/**
 * Inline note shown by lineup-derived views that leave out seasons whose player
 * scores aren't loaded yet (frontend/lineup-data-status). Renders nothing when no
 * season is excluded.
 */
export function LineupPendingNote({ seasons }: { seasons: string[] }) {
  if (seasons.length === 0) return null;
  return (
    <div
      role="note"
      className="flex items-center gap-2 rounded-md border border-border/50 bg-muted px-3 py-2 text-[12px] text-muted-foreground"
    >
      <Hourglass className="size-3.5 shrink-0" aria-hidden="true" />
      <span>
        Player scores for {formatSeasons(seasons)} are still loading, so{' '}
        {seasons.length === 1 ? 'that season is' : 'those seasons are'} left out
        here for now.
      </span>
    </div>
  );
}
