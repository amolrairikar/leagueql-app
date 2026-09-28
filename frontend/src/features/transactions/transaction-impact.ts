import {
  type TransactionItem,
  type TransactionPlayer,
  type WeeklyPlayerPoints,
  rosPointsFor,
} from '@/features/transactions/api-calls';

/** Rounds a points total to 2 decimal places, matching how the cards display ROS points. */
function round2(value: number): number {
  return Math.round(value * 100) / 100;
}

/** All roster_ids touched by a transaction, in the order teams are listed. */
export function involvedRosterIds(txn: TransactionItem): string[] {
  const ids = new Set<string>();
  for (const team of txn.teams) ids.add(team.roster_id);
  for (const add of txn.adds) ids.add(add.roster_id);
  for (const drop of txn.drops) ids.add(drop.roster_id);
  return [...ids];
}

export function teamLabel(
  txn: TransactionItem,
  rosterId: string | null,
): string {
  if (rosterId === null) return 'Unknown team';
  const team = txn.teams.find((t) => t.roster_id === rosterId);
  if (!team) return `Roster ${rosterId}`;
  // Prefer the display name, then the team name, ignoring null/empty values.
  return (
    [team.display_name, team.team_name].find((n) => n) ?? `Roster ${rosterId}`
  );
}

/** Sum of the points a roster's acquired players scored while on that roster, for a trade. */
export function sideTotal(
  txn: TransactionItem,
  rosterId: string,
  weekly: WeeklyPlayerPoints,
  exits: RosterExits,
): number {
  const total = txn.adds
    .filter((a) => a.roster_id === rosterId)
    .reduce((sum, a) => sum + pointsWhileRostered(txn, a, weekly, exits), 0);
  return round2(total);
}

/**
 * Every time a player left a roster during the season, keyed `${rosterId}:${playerId}`, sorted by
 * `created`. Built from the `drops` of every transaction type (a trade's drops are the players each
 * side sent away), so it bounds how long an added player stayed on the acquiring roster.
 */
export type RosterExits = Map<string, { week: number; created: number }[]>;

export function buildRosterExits(transactions: TransactionItem[]): RosterExits {
  const exits: RosterExits = new Map();
  for (const txn of transactions) {
    for (const drop of txn.drops) {
      const key = `${drop.roster_id}:${drop.player_id}`;
      let list = exits.get(key);
      if (!list) {
        list = [];
        exits.set(key, list);
      }
      list.push({ week: txn.week ?? 0, created: txn.created });
    }
  }
  for (const list of exits.values()) list.sort((a, b) => a.created - b.created);
  return exits;
}

/**
 * The week a player next left `rosterId` after the transaction created at `afterCreated`, or
 * `Infinity` if he stayed through the end of the season. That week belongs to the next owner
 * (the page's convention that a transaction's week counts for the receiving side), so it is used
 * as an exclusive upper bound.
 */
export function exitWeek(
  exits: RosterExits,
  rosterId: string,
  playerId: string,
  afterCreated: number,
): number {
  const next = exits
    .get(`${rosterId}:${playerId}`)
    ?.find((e) => e.created > afterCreated);
  return next?.week ?? Infinity;
}

/**
 * Points a player acquired in `txn` (waiver / free-agent add or trade acquisition) scored while on
 * the acquiring roster: from the move's week up to (not including) the week of the next
 * transaction that dropped or traded him away.
 */
export function pointsWhileRostered(
  txn: TransactionItem,
  player: TransactionPlayer,
  weekly: WeeklyPlayerPoints,
  exits: RosterExits,
): number {
  return rosPointsFor(
    player.player_id,
    txn.week ?? 0,
    weekly,
    exitWeek(exits, player.roster_id, player.player_id, txn.created),
  );
}

/**
 * The net pickup value of a waiver / free-agent move for one roster: the points its acquired
 * player(s) scored while on the roster minus the rest-of-season points its released player(s)
 * scored. A pure add resolves to the added total, a pure drop to the negative of the dropped total.
 */
export function netPickupValue(
  txn: TransactionItem,
  rosterId: string,
  weekly: WeeklyPlayerPoints,
  exits: RosterExits,
): number {
  const week = txn.week ?? 0;
  const added = txn.adds
    .filter((p) => p.roster_id === rosterId)
    .reduce((sum, p) => sum + pointsWhileRostered(txn, p, weekly, exits), 0);
  const dropped = txn.drops
    .filter((p) => p.roster_id === rosterId)
    .reduce((sum, p) => sum + rosPointsFor(p.player_id, week, weekly), 0);
  return round2(added - dropped);
}

export interface TransactionImpact {
  txn: TransactionItem;
  /** The roster credited with the move: the waiver/FA roster, or a trade's winning side. */
  rosterId: string;
  /** For a trade, the losing side; null for a waiver / free agent. */
  opponentRosterId: string | null;
  /** Net pickup value (waiver / FA) or winning margin (trade), in fantasy points. */
  value: number;
}

/**
 * A transaction's impact on the single points scale the Top transactions highlight ranks by, or
 * null when it has none: a waiver / free agent's net pickup value, or a two-team trade's winning
 * margin credited to the winner. Multi-team trades, commissioner moves, and even trades have none.
 */
export function transactionImpact(
  txn: TransactionItem,
  weekly: WeeklyPlayerPoints,
  exits: RosterExits,
): TransactionImpact | null {
  const rosterIds = involvedRosterIds(txn);
  if (txn.type === 'waiver' || txn.type === 'free_agent') {
    if (rosterIds.length !== 1) return null;
    return {
      txn,
      rosterId: rosterIds[0],
      opponentRosterId: null,
      value: netPickupValue(txn, rosterIds[0], weekly, exits),
    };
  }
  if (txn.type === 'trade' && rosterIds.length === 2) {
    const [a, b] = rosterIds.map((rid) => sideTotal(txn, rid, weekly, exits));
    if (a === b) return null;
    const winner = a > b ? 0 : 1;
    return {
      txn,
      rosterId: rosterIds[winner],
      opponentRosterId: rosterIds[1 - winner],
      value: round2(Math.abs(a - b)),
    };
  }
  return null;
}

/**
 * The season's top `n` moves by impact, highest first (earlier transaction first on a tie). Only
 * moves with a positive impact are eligible.
 */
export function topTransactions(
  transactions: TransactionItem[],
  weekly: WeeklyPlayerPoints,
  n = 5,
): TransactionImpact[] {
  const exits = buildRosterExits(transactions);
  return transactions
    .map((txn) => transactionImpact(txn, weekly, exits))
    .filter((impact): impact is TransactionImpact => impact != null)
    .filter((impact) => impact.value > 0)
    .sort((x, y) => y.value - x.value || x.txn.created - y.txn.created)
    .slice(0, n);
}
