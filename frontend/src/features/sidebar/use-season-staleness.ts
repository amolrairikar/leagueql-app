import { useState } from 'react';

import { getLeagueCookies, isDemoMode } from '@/lib/cookie-handler';
import { currentFantasySeason } from '@/lib/season';

export interface SeasonStalenessState {
  /**
   * Whether the current fantasy season is after the league's latest onboarded
   * season. False in the bypass cases (demo mode / no league) and for a league
   * with no onboarded seasons (frontend/sleeper-stale-season-banner).
   */
  isStaleSeason: boolean;
}

/**
 * Reports whether the current league's latest onboarded season is behind the
 * current fantasy season, so the Sleeper stale-season banner
 * (frontend/sleeper-stale-season-banner) can decide whether to show. Both inputs
 * are available locally — the onboarded `seasons` from `getLeagueCookies()` and
 * the current season from the clock — so no fetch is needed. Demo mode and the
 * "no league connected" case bypass to not-stale.
 */
export function useSeasonStaleness(): SeasonStalenessState {
  const demoMode = isDemoMode();
  const { leagueId, seasons } = getLeagueCookies();

  // Read the clock once on mount (a lazy initializer keeps the side-effecting
  // read out of the render body); it does not change while the banner is shown.
  const [currentSeason] = useState(() => currentFantasySeason(new Date()));

  const isStaleSeason =
    !demoMode &&
    !!leagueId &&
    seasons.length > 0 &&
    Math.max(...seasons.map(Number)) < currentSeason;

  return { isStaleSeason };
}
