import { queryLeague } from '@/components/api/leagues';
import type { Platform } from '@/components/api/types';
import { ApiError } from '@/lib/api-client';

/** A single week's recap (FE-033 / BE-022). */
export interface RecapItem {
  season: string;
  week: string;
  headline: string;
  body: string;
  model: string;
  generated_at: string;
}

/** Zero-pad a week number to the `WEEK#WW` form used in the RECAP sort key. */
function padWeek(week: number): string {
  return String(week).padStart(2, '0');
}

/**
 * Fetch the stored recap for a single season/week (FE-033). Resolves to the recap
 * object, or `null` when none has been generated yet (the query returns an empty
 * list / 404 → empty state, not an error).
 */
export function getWeekRecap(
  leagueId: string,
  platform: Platform,
  season: string,
  week: number,
): Promise<RecapItem | null> {
  return queryLeague<RecapItem>(
    leagueId,
    platform,
    `RECAP#${season}#WEEK#${padWeek(week)}`,
  )
    .then((res) => res.data[0] ?? null)
    .catch((err: unknown) => {
      // A week with no generated recap yet 404s — a legitimate empty result, not
      // an error. Any other failure propagates so the section shows an inline error.
      if (err instanceof ApiError && err.status === 404) return null;
      throw err;
    });
}
