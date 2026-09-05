import { useEffect, useState } from 'react';

import { getLeague } from '@/components/api/leagues';
import { getLeagueCookies, isDemoMode } from '@/lib/cookie-handler';

// A league's data is considered stale once it has not been updated in more than 7
// days. This mirrors the backend's weekly refresh cooldown (backend/league-refresh),
// so the reminder only appears when a manual refresh is actually permitted.
const STALE_AFTER_MS = 7 * 24 * 60 * 60 * 1000;

export interface LeagueFreshnessState {
  /** True while `getLeague` is in flight (never true for the bypass cases). */
  loading: boolean;
  /**
   * Whether the league's data is more than 7 days old, derived from
   * `last_refresh_at` (falling back to `onboarded_at` for a never-refreshed
   * league). False while loading, for the bypass cases, or when no timestamp is
   * available (frontend/refresh-reminder-banner).
   */
  isStale: boolean;
}

function parseDate(value?: string | null): Date | null {
  if (!value) return null;
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? null : d;
}

/**
 * Reads the current league's data-freshness timestamp (from `GET /leagues/{id}`)
 * and reports whether the data is stale, so the refresh reminder
 * (frontend/refresh-reminder-banner) can decide whether to show. Freshness is
 * `last_refresh_at ?? onboarded_at`. Demo mode and the "no league connected" case
 * bypass the fetch; a failed request resolves to not-stale so the banner stays
 * hidden.
 */
export function useLeagueFreshness(): LeagueFreshnessState {
  const demoMode = isDemoMode();
  const { leagueId, platform } = getLeagueCookies();
  const bypass = demoMode || !leagueId;

  const [state, setState] = useState<LeagueFreshnessState>(
    bypass
      ? { loading: false, isStale: false }
      : { loading: true, isStale: false },
  );

  useEffect(() => {
    if (bypass) return;
    let cancelled = false;
    getLeague(leagueId, platform)
      .then((res) => {
        if (cancelled) return;
        const lastUpdated =
          parseDate(res.data.last_refresh_at) ??
          parseDate(res.data.onboarded_at);
        // Compute freshness here (in the effect) rather than during render so the
        // component stays pure — Date.now() is a side-effecting read.
        const isStale =
          lastUpdated !== null &&
          Date.now() - lastUpdated.getTime() > STALE_AFTER_MS;
        setState({ loading: false, isStale });
      })
      .catch(() => {
        if (!cancelled) setState({ loading: false, isStale: false });
      });
    return () => {
      cancelled = true;
    };
  }, [bypass, leagueId, platform]);

  return state;
}
