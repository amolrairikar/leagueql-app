import { useEffect, useState } from 'react';

import { getLeague } from '@/components/api/leagues';
import { getLeagueCookies, isDemoMode } from '@/lib/cookie-handler';

export interface OwnershipState {
  /** True while `getLeague` is in flight (never true for the bypass cases). */
  loading: boolean;
  /** Whether the authenticated caller owns the current league (backend/league-authorization / frontend/ownership-transfer). */
  isOwner: boolean;
}

/**
 * Reads the current league's `is_owner` flag (from `GET /leagues/{id}`) so the
 * sidebar can show owner-only affordances only to the owner. Demo mode and the
 * "no league connected" case bypass the fetch (the demo sidebar uses a separate
 * branch); a failed request resolves to non-owner so owner actions stay hidden.
 */
export function useIsOwner(): OwnershipState {
  const demoMode = isDemoMode();
  const { leagueId, platform } = getLeagueCookies();
  const bypass = demoMode || !leagueId;

  const [state, setState] = useState<OwnershipState>(
    bypass
      ? { loading: false, isOwner: true }
      : { loading: true, isOwner: false },
  );

  useEffect(() => {
    if (bypass) return;
    let cancelled = false;
    getLeague(leagueId, platform)
      .then((res) => {
        if (!cancelled)
          setState({ loading: false, isOwner: res.data.is_owner === true });
      })
      .catch(() => {
        if (!cancelled) setState({ loading: false, isOwner: false });
      });
    return () => {
      cancelled = true;
    };
  }, [bypass, leagueId, platform]);

  return state;
}
