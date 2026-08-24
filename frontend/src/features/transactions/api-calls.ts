import { queryLeague } from '@/components/api/leagues';
import type { Platform, TransactionItem } from '@/components/api/types';
import { ApiError } from '@/lib/api-client';

export type {
  TransactionItem,
  TransactionPlayer,
  TransactionTeam,
  TransactionDraftPick,
} from '@/components/api/types';

export interface GetTransactionsResponse {
  data: TransactionItem[];
}

/**
 * Fetch a season's transactions (waivers, trades, free agents) for a league.
 *
 * Sleeper-only (backend/sleeper-transactions / frontend/transactions). A season with no completed transactions has no
 * TRANSACTIONS item and 404s; that is a legitimate empty result, so a 404 resolves to an
 * empty list. Any other failure propagates so the page can show an inline error.
 */
export function getTransactions(
  leagueId: string,
  platform: Platform,
  season: string,
): Promise<GetTransactionsResponse> {
  return queryLeague<TransactionItem>(
    leagueId,
    platform,
    `TRANSACTIONS#${season}`,
  ).catch((err: unknown) => {
    if (err instanceof ApiError && err.status === 404) {
      return { data: [] as TransactionItem[] };
    }
    throw err;
  });
}
