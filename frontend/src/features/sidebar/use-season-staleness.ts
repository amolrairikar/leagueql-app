import { useState } from 'react';

import { getLeagueCookies, isDemoMode } from '@/lib/cookie-handler';

export interface SeasonStalenessState {
  /**
   * Whether the current fantasy season is after the league's latest onboarded
   * season. False in the bypass cases (demo mode / no league) and for a league
   * with no onboarded seasons (frontend/sleeper-stale-season-banner).
   */
  isStaleSeason: boolean;
}

/**
 * Returns the current fantasy season (NFL season year) from `now`. The NFL
 * season flips in September, so before September the current fantasy season is
 * still the prior calendar year — this mirrors the backend's current-season
 * gate (`nfl_state["season"]`, src/sleeper_refresh).
 */
function currentFantasySeason(now: Date): number {
  const year = now.getFullYear();
  return now.getMonth() >= 8 ? year : year - 1;
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
