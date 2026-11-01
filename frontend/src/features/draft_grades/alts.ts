import { type DraftPickItem } from './api-calls';

import { ALT_PICK_ROUND_WINDOW } from '@/features/draft_grades/constants';

export function getAlts(
  pick: DraftPickItem,
  allPicks: DraftPickItem[],
  isAuction: boolean,
): DraftPickItem[] {
  // A pick with no scoring row has no point total to compare against, so it can
  // neither be an alternative nor have alternatives suggested for it.
  if (pick.total_points == null) return [];
  // Keepers occupy a slot fixed by last year's draft, so nobody else could have
  // been taken there — a keeper bust has no alternatives, and a keeper was never
  // available to suggest as one.
  if (pick.keeper) return [];
  return allPicks
    .filter((a) =>
      a.total_points == null || a.keeper
        ? false
        : isAuction
          ? a.position === pick.position &&
            a.player_name !== pick.player_name &&
            a.team_id !== pick.team_id &&
            a.bid_amount <= pick.bid_amount &&
            a.total_points > pick.total_points!
          : a.position === pick.position &&
            a.overall_pick_number > pick.overall_pick_number &&
            a.round <= pick.round + ALT_PICK_ROUND_WINDOW &&
            a.player_name !== pick.player_name &&
            a.team_id !== pick.team_id &&
            a.total_points > pick.total_points!,
    )
    .sort((a, b) => (b.total_points ?? 0) - (a.total_points ?? 0))
    .slice(0, 2);
}

// ── Skeleton ──────────────────────────────────────────────────────────────────
