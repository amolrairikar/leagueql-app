/**
 * Trade-value computation (frontend/transactions) — pure, no I/O.
 *
 * Extracted from `transactions.tsx` so both the Transactions page and the My Team
 * report card evaluate a trade from one shared implementation. A trade side's value
 * is the total rest-of-season fantasy points the players it acquired went on to
 * score from the trade's week onward (see `rosPointsFor` in ./api-calls).
 */
import { type WeeklyPlayerPoints, rosPointsFor } from './api-calls';

import type { TransactionItem } from '@/components/api/types';

/** All roster_ids touched by a transaction, in the order teams are listed. */
export function involvedRosterIds(txn: TransactionItem): string[] {
  const ids = new Set<string>();
  for (const team of txn.teams) ids.add(team.roster_id);
  for (const add of txn.adds) ids.add(add.roster_id);
  for (const drop of txn.drops) ids.add(drop.roster_id);
  return [...ids];
}

/** Sum of the rest-of-season points a roster's acquired players scored, for a trade. */
export function tradeValueForRoster(
  txn: TransactionItem,
  rosterId: string,
  weekly: WeeklyPlayerPoints,
): number {
  const total = txn.adds
    .filter((a) => a.roster_id === rosterId)
    .reduce(
      (sum, a) => sum + rosPointsFor(a.player_id, txn.week ?? 0, weekly),
      0,
    );
  return Math.round(total * 100) / 100;
}

export interface TradeEvaluation {
  /** Side totals aligned to the passed `rosterIds`. */
  totals: number[];
  /** Index of the higher-scoring side; null on a tie or when not exactly two sides. */
  winnerIndex: number | null;
  /** Absolute point margin between the two sides; null when there is no winner. */
  margin: number | null;
}

/** Evaluate a two-team trade: each side's total, the winner, and the margin. */
export function evaluateTrade(
  txn: TransactionItem,
  rosterIds: string[],
  weekly: WeeklyPlayerPoints,
): TradeEvaluation {
  const totals = rosterIds.map((rid) => tradeValueForRoster(txn, rid, weekly));
  const winnerIndex =
    totals.length === 2 && totals[0] !== totals[1]
      ? totals[0] > totals[1]
        ? 0
        : 1
      : null;
  const margin =
    winnerIndex !== null
      ? Math.round(Math.abs(totals[0] - totals[1]) * 100) / 100
      : null;
  return { totals, winnerIndex, margin };
}

/**
 * Net rest-of-season value of a two-team trade *for one roster*: the points its
 * acquired players scored minus the points the other side's acquired players
 * scored (i.e. what it gave up). Positive means the roster came out ahead.
 * Returns null when the transaction is not a two-team trade involving `rosterId`.
 */
export function netTradeValueForRoster(
  txn: TransactionItem,
  rosterId: string,
  weekly: WeeklyPlayerPoints,
): number | null {
  if (txn.type !== 'trade') return null;
  const ids = involvedRosterIds(txn);
  if (ids.length !== 2 || !ids.includes(rosterId)) return null;
  const other = ids.find((id) => id !== rosterId)!;
  const net =
    tradeValueForRoster(txn, rosterId, weekly) -
    tradeValueForRoster(txn, other, weekly);
  return Math.round(net * 100) / 100;
}
