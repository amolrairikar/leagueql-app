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
  /**
   * Whether the owner's stored ESPN cookies were rejected (or are missing) for this
   * auto-refreshed ESPN league (`espn_reauth_required`), so scheduled refresh is
   * paused until they re-enter them. Drives the re-auth banner and the sidebar's
   * Update ESPN Cookies action. False for the bypass cases and on a failed fetch.
   */
  espnReauthRequired: boolean;
}

/**
 * Reads the current league's `is_owner`, `auto_refresh_enabled`, and
 * `espn_reauth_required` flags (from
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
      ? {
          loading: false,
          isOwner: true,
          autoRefreshEnabled: false,
          espnReauthRequired: false,
        }
      : {
          loading: true,
          isOwner: false,
          autoRefreshEnabled: false,
          espnReauthRequired: false,
        },
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
            espnReauthRequired: res.data.espn_reauth_required === true,
          });
      })
      .catch(() => {
        if (!cancelled)
          setState({
            loading: false,
            isOwner: false,
            autoRefreshEnabled: false,
            espnReauthRequired: false,
          });
      });
    return () => {
      cancelled = true;
    };
  }, [bypass, leagueId, platform]);

  return state;
}
