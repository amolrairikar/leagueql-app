import { describe, expect, it } from 'vitest';

import { type WeeklyPlayerPoints } from '../api-calls';
import {
  evaluateTrade,
  involvedRosterIds,
  netTradeValueForRoster,
  tradeValueForRoster,
} from '../compute-trade-value';

import type {
  TransactionItem,
  TransactionPlayer,
} from '@/components/api/types';

function add(playerId: string, rosterId: string): TransactionPlayer {
  return {
    player_id: playerId,
    player_name: `P${playerId}`,
    position: 'RB',
    roster_id: rosterId,
  };
}

function trade(week: number, adds: TransactionPlayer[]): TransactionItem {
  const rosterIds = [...new Set(adds.map((a) => a.roster_id))];
  return {
    season: '2024',
    transaction_id: 'tx1',
    type: 'trade',
    week,
    created: 0,
    roster_ids: rosterIds,
    teams: rosterIds.map((rid) => ({
      roster_id: rid,
      team_name: `Team ${rid}`,
      display_name: `mgr${rid}`,
    })),
    adds,
    drops: [],
    draft_picks: [],
    waiver_bid: null,
  };
}

/** Build WeeklyPlayerPoints from a nested playerId → week → points record. */
function weeklyOf(
  data: Record<string, Record<number, number>>,
): WeeklyPlayerPoints {
  const m: WeeklyPlayerPoints = new Map();
  for (const [pid, weeks] of Object.entries(data)) {
    m.set(pid, new Map(Object.entries(weeks).map(([w, p]) => [Number(w), p])));
  }
  return m;
}

describe('compute-trade-value', () => {
  // Trade in week 3: A→roster r1, B→roster r2.
  const txn = trade(3, [add('A', 'r1'), add('B', 'r2')]);
  const weekly = weeklyOf({
    A: { 2: 10, 3: 20, 4: 30 }, // only weeks >= 3 count: 50
    B: { 3: 5, 4: 5 }, // 10
  });

  it('sums rest-of-season points from the trade week onward per roster', () => {
    expect(tradeValueForRoster(txn, 'r1', weekly)).toBe(50);
    expect(tradeValueForRoster(txn, 'r2', weekly)).toBe(10);
  });

  it('evaluates the winner and margin of a two-team trade', () => {
    const evalResult = evaluateTrade(txn, involvedRosterIds(txn), weekly);
    expect(evalResult.totals).toEqual([50, 10]);
    expect(evalResult.winnerIndex).toBe(0);
    expect(evalResult.margin).toBe(40);
  });

  it('reports no winner on a tie', () => {
    const tie = trade(1, [add('A', 'r1'), add('B', 'r2')]);
    const tieWeekly = weeklyOf({ A: { 1: 10 }, B: { 1: 10 } });
    const evalResult = evaluateTrade(tie, involvedRosterIds(tie), tieWeekly);
    expect(evalResult.winnerIndex).toBeNull();
    expect(evalResult.margin).toBeNull();
  });

  it('computes net value for a roster (mine − theirs)', () => {
    expect(netTradeValueForRoster(txn, 'r1', weekly)).toBe(40);
    expect(netTradeValueForRoster(txn, 'r2', weekly)).toBe(-40);
  });

  it('returns null net for a non-two-team trade', () => {
    const threeWay = trade(1, [add('A', 'r1'), add('B', 'r2'), add('C', 'r3')]);
    expect(netTradeValueForRoster(threeWay, 'r1', weekly)).toBeNull();
  });
});
