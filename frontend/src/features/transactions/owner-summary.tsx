import { type ReactNode } from 'react';

import {
  type TransactionItem,
  type TransactionPlayer,
  type TransactionTeam,
} from '@/features/transactions/api-calls';
import { involvedRosterIds } from '@/features/transactions/transaction-impact';

export function playerLabel(player: TransactionPlayer): ReactNode {
  const name = player.player_name ?? `Player ${player.player_id}`;
  return (
    <span>
      {name}
      {player.position && (
        <span className="text-muted-foreground font-normal">
          {' '}
          {player.position}
        </span>
      )}
    </span>
  );
}

/** The type columns the summary table tracks (commissioner moves are excluded). */
export type SummaryType = 'waiver' | 'free_agent' | 'trade';

export interface OwnerSummaryRow {
  rosterId: string;
  ownerUsername: string;
  teamName: string;
  waiver: number;
  free_agent: number;
  trade: number;
  total: number;
}

/**
 * Per-owner activity for the season, counted per transaction: each waiver, free-agent, or
 * trade transaction adds 1 to the matching column for every owner it involves. Only owners
 * that appear in at least one transaction are included; rows are sorted by total descending,
 * then owner name ascending. Commissioner transactions are ignored.
 */
export function buildOwnerSummary(
  transactions: TransactionItem[],
): OwnerSummaryRow[] {
  // Resolve each roster's team from every transaction it appears in, so the row can show the
  // owner username and team name (matching the other tables, e.g. Season Standings).
  const teams = new Map<string, TransactionTeam>();
  for (const txn of transactions) {
    for (const team of txn.teams) teams.set(team.roster_id, team);
  }

  const rows = new Map<string, OwnerSummaryRow>();
  const rowFor = (rosterId: string): OwnerSummaryRow => {
    let row = rows.get(rosterId);
    if (!row) {
      const team = teams.get(rosterId);
      const ownerUsername =
        [team?.display_name, team?.team_name].find((n) => n) ??
        `Roster ${rosterId}`;
      row = {
        rosterId,
        ownerUsername,
        teamName: [team?.team_name].find((n) => n) ?? `Team ${ownerUsername}`,
        waiver: 0,
        free_agent: 0,
        trade: 0,
        total: 0,
      };
      rows.set(rosterId, row);
    }
    return row;
  };

  for (const txn of transactions) {
    if (
      txn.type !== 'waiver' &&
      txn.type !== 'free_agent' &&
      txn.type !== 'trade'
    ) {
      continue;
    }
    const type: SummaryType = txn.type;
    for (const rosterId of involvedRosterIds(txn)) {
      const row = rowFor(rosterId);
      row[type] += 1;
      row.total += 1;
    }
  }

  return [...rows.values()].sort(
    (a, b) =>
      b.total - a.total || a.ownerUsername.localeCompare(b.ownerUsername),
  );
}
