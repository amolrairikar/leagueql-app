import { useEffect, useState } from 'react';

import { getLeague } from '@/components/api/leagues';
import { getLeagueCookies, isDemoMode } from '@/lib/cookie-handler';

export interface LineupBackfillState {
  /** Seasons whose weekly player scores are still being backfilled (ascending). */
  pendingSeasons: string[];
  /** Seasons whose backfill couldn't finish yet; retried automatically (ascending). */
  failedSeasons: string[];
  /**
   * Whether a season's lineups (starters/bench + player points) are not available
   * yet — pending or failed (frontend/lineup-data-status). Lineup-dependent views
   * show a placeholder / exclude the season instead of zero-point lineups.
   */
  isLineupUnavailable: (season: string | number) => boolean;
}

const EMPTY: Omit<LineupBackfillState, 'isLineupUnavailable'> = {
  pendingSeasons: [],
  failedSeasons: [],
};

/**
 * Reads the current league's lineup backfill status (from `GET /leagues/{id}`).
 * Only Yahoo leagues backfill lineups (backend/yahoo-lineup-backfill), so demo
 * mode, no connected league, and ESPN/Sleeper leagues bypass the fetch. The API
 * client dedupes/caches the GET, so every lineup-dependent component on a page
 * shares one request. A failed request resolves to nothing pending.
 */
export function useLineupBackfill(): LineupBackfillState {
  const { leagueId, platform } = getLeagueCookies();
  const bypass = isDemoMode() || !leagueId || platform !== 'YAHOO';

  const [status, setStatus] = useState(EMPTY);

  useEffect(() => {
    if (bypass) return;
    let cancelled = false;
    getLeague(leagueId, platform)
      .then((res) => {
        if (cancelled) return;
        setStatus({
          pendingSeasons: res.data.pending_lineup_seasons ?? [],
          failedSeasons: res.data.failed_lineup_seasons ?? [],
        });
      })
      .catch(() => {
        if (!cancelled) setStatus(EMPTY);
      });
    return () => {
      cancelled = true;
    };
  }, [bypass, leagueId, platform]);

  const current = bypass ? EMPTY : status;
  return {
    ...current,
    isLineupUnavailable: (season) =>
      current.pendingSeasons.includes(String(season)) ||
      current.failedSeasons.includes(String(season)),
  };
}

/** Formats seasons for display, collapsing consecutive years ("2019–2021, 2024"). */
export function formatSeasons(seasons: string[]): string {
  const years = [...new Set(seasons.map(Number))].sort((a, b) => a - b);
  const ranges: string[] = [];
  let start = years[0];
  let prev = years[0];
  for (const year of years.slice(1).concat(NaN)) {
    if (year === prev + 1) {
      prev = year;
      continue;
    }
    ranges.push(start === prev ? String(start) : `${start}–${prev}`);
    start = year;
    prev = year;
  }
  return years.length ? ranges.join(', ') : '';
}
