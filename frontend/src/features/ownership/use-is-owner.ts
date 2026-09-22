import { useEffect, useState } from 'react';

import { getLeague } from '@/components/api/leagues';
import { getLeagueCookies, isDemoMode } from '@/lib/cookie-handler';

export interface OwnershipState {
  /** True while `getLeague` is in flight (never true for the bypass cases). */
  loading: boolean;
  /** Whether the authenticated caller owns the current league (backend/league-authorization / frontend/ownership-transfer). */
  isOwner: boolean;
  /**
   * Whether the current league is enrolled in scheduled auto-refresh
   * (`auto_refresh_enabled`). Drives hiding the sidebar's manual Refresh League
   * action and the refresh-reminder banner for auto-refreshed ESPN leagues.
   * False for the bypass cases and on a failed fetch.
   */
  autoRefreshEnabled: boolean;
}

/**
 * Reads the current league's `is_owner` and `auto_refresh_enabled` flags (from
 * `GET /leagues/{id}`) so the sidebar can show owner-only affordances only to the
 * owner and hide the manual refresh action for auto-refreshed leagues. Demo mode
 * and the "no league connected" case bypass the fetch (the demo sidebar uses a
 * separate branch); a failed request resolves to non-owner / not-auto-refreshed so
 * owner actions stay hidden.
 */
export function useIsOwner(): OwnershipState {
  const demoMode = isDemoMode();
  const { leagueId, platform } = getLeagueCookies();
  const bypass = demoMode || !leagueId;

  const [state, setState] = useState<OwnershipState>(
    bypass
      ? { loading: false, isOwner: true, autoRefreshEnabled: false }
      : { loading: true, isOwner: false, autoRefreshEnabled: false },
  );

  useEffect(() => {
    if (bypass) return;
    let cancelled = false;
    getLeague(leagueId, platform)
      .then((res) => {
        if (!cancelled)
          setState({
            loading: false,
            isOwner: res.data.is_owner === true,
            autoRefreshEnabled: res.data.auto_refresh_enabled === true,
          });
      })
      .catch(() => {
        if (!cancelled)
          setState({
            loading: false,
            isOwner: false,
            autoRefreshEnabled: false,
          });
      });
    return () => {
      cancelled = true;
    };
  }, [bypass, leagueId, platform]);

  return state;
}
