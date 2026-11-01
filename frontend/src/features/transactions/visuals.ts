import { type SeasonStandingsItem } from '@/features/season_standings/api-calls';
import { type TransactionItem } from '@/features/transactions/api-calls';
import { involvedRosterIds } from '@/features/transactions/transaction-impact';

export interface OwnerVisual {
  /** Index into the standings order, so `avatarColor(index)` matches the standings page. */
  colorIndex: number;
  teamLogo: string;
}

/**
 * Maps each roster_id to the avatar logo and color *index* used on the Season Standings page
 * (frontend/season-standings), so the summary table shows the same avatar/color per owner. Standings keys on
 * team_id, which is the transaction roster_id (Sleeper roster id / ESPN team id), and its
 * color is positional — `avatarColor(index)` over the API's returned order — so the index is
 * captured here rather than the resolved color.
 */
export function buildStandingsVisuals(
  standings: SeasonStandingsItem[],
): Map<string, OwnerVisual> {
  return new Map(
    standings.map((s, i): [string, OwnerVisual] => [
      s.team_id,
      { colorIndex: i, teamLogo: s.team_logo },
    ]),
  );
}

/**
 * Avatar visuals for the transaction cards. Every roster that appears in a transaction gets a
 * color, so a card can render an avatar even when standings is missing: rosters are seeded in
 * first-appearance order, then Season Standings visuals (logo + positional color) are overlaid so
 * a roster present in standings matches its Season Standings / summary-table avatar exactly.
 */
export function buildTransactionVisuals(
  transactions: TransactionItem[],
  standings: SeasonStandingsItem[],
): Map<string, OwnerVisual> {
  const visuals = new Map<string, OwnerVisual>();
  let i = 0;
  for (const txn of transactions) {
    for (const rosterId of involvedRosterIds(txn)) {
      if (!visuals.has(rosterId)) {
        visuals.set(rosterId, { colorIndex: i++, teamLogo: '' });
      }
    }
  }
  standings.forEach((s, idx) =>
    visuals.set(s.team_id, { colorIndex: idx, teamLogo: s.team_logo }),
  );
  return visuals;
}
