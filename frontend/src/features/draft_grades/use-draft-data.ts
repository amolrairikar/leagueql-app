import { useMemo, useState } from 'react';

import {
  type DraftPickItem,
  getDraftData,
} from '@/features/draft_grades/api-calls';
import { getLeagueCookies, isDemoMode } from '@/lib/cookie-handler';
import { type Result } from '@/lib/result';
import { latestSeason, seasonQuery } from '@/lib/season';

export type DraftResult = Result<DraftPickItem[]>;

/**
 * Shared bootstrap for the draft feature pages (draft grades, draft recap).
 *
 * Reads the active league from cookies, seeds the selected season to the latest,
 * tracks the demo-only auction toggle, and builds the never-rejecting draft-data
 * promise both pages consume via Suspense. Keeps the two pages — which differ
 * only in layout and downstream rendering — from re-deriving identical state.
 */
export function useDraftData() {
  const { leagueId, platform, seasons } = useMemo(() => getLeagueCookies(), []);
  const isDemo = useMemo(() => isDemoMode(), []);

  const [selectedSeason, setSelectedSeason] = useState(latestSeason(seasons));
  // Demo-only toggle: selects the separate DRAFT_AUCTION dataset.
  const [demoAuction, setDemoAuction] = useState(false);

  const draftPromise = useMemo(
    (): Promise<DraftResult> =>
      seasonQuery(
        Boolean(leagueId && selectedSeason),
        () =>
          getDraftData(
            leagueId,
            platform,
            selectedSeason,
            isDemo && demoAuction,
          ),
        'Failed to load draft data.',
      ),
    [leagueId, platform, selectedSeason, isDemo, demoAuction],
  );

  return {
    leagueId,
    platform,
    seasons,
    isDemo,
    selectedSeason,
    setSelectedSeason,
    demoAuction,
    setDemoAuction,
    draftPromise,
  };
}
