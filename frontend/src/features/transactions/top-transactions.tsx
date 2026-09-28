import { ArrowDown, ArrowUp } from 'lucide-react';

import { TeamAvatar } from '@/components/team-avatar';
import {
  type TransactionItem,
  type TransactionPlayer,
  type WeeklyPlayerPoints,
} from '@/features/transactions/api-calls';
import {
  type TransactionImpact,
  teamLabel,
  topTransactions,
} from '@/features/transactions/transaction-impact';
import { typeMeta } from '@/features/transactions/type-meta';
import { avatarColor } from '@/lib/color-constants';
import { cn } from '@/lib/utils';

type Visuals = Map<string, { colorIndex: number; teamLogo: string }>;

function playerText(player: TransactionPlayer): string {
  const name = player.player_name ?? `Player ${player.player_id}`;
  return player.position ? `${name} ${player.position}` : name;
}

function pickText(pick: TransactionItem['draft_picks'][number]): string {
  return `${pick.season} Rd ${pick.round} pick`;
}

/**
 * What the credited roster brought in and let go. For a waiver / free agent that is its own adds and
 * drops; for a trade it is what the winner received vs. what the opponent received from it.
 */
function movesFor({ txn, rosterId, opponentRosterId }: TransactionImpact): {
  added: string[];
  dropped: string[];
} {
  const addsTo = (rid: string) => [
    ...txn.adds.filter((p) => p.roster_id === rid).map(playerText),
    ...txn.draft_picks.filter((p) => p.to_roster_id === rid).map(pickText),
  ];
  if (opponentRosterId !== null) {
    return { added: addsTo(rosterId), dropped: addsTo(opponentRosterId) };
  }
  return {
    added: txn.adds.filter((p) => p.roster_id === rosterId).map(playerText),
    dropped: txn.drops.filter((p) => p.roster_id === rosterId).map(playerText),
  };
}

function TopTile({
  impact,
  rank,
  visuals,
}: {
  impact: TransactionImpact;
  rank: number;
  visuals: Visuals;
}) {
  const { txn, rosterId, opponentRosterId, value } = impact;
  const meta = typeMeta(txn.type);
  const isTop = rank === 1;
  const isTrade = opponentRosterId !== null;
  const visual = visuals.get(rosterId);
  const team = txn.teams.find((t) => t.roster_id === rosterId);
  const name = teamLabel(txn, rosterId);
  const { added, dropped } = movesFor(impact);

  const context = isTrade
    ? `vs ${teamLabel(txn, opponentRosterId)}`
    : txn.waiver_bid != null && txn.waiver_bid > 0
      ? `$${txn.waiver_bid} FAAB`
      : null;

  return (
    <li
      className={cn(
        'min-w-0 flex flex-col gap-2.5 rounded-xl border p-3.5 shadow-sm',
        isTop
          ? 'col-span-2 sm:col-span-1 border-emerald-500/30 bg-emerald-500/5'
          : 'bg-card border-border/50',
      )}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-[12px] font-bold text-muted-foreground tabular-nums">
          #{rank}
        </span>
        <span
          className={cn(
            'inline-flex items-center gap-1 text-[10.5px] font-semibold px-2 py-0.5 rounded-full',
            meta.chip,
          )}
        >
          <meta.Icon className="w-3 h-3" />
          {meta.label}
        </span>
      </div>

      <div className="flex flex-col">
        <span className="text-[22px] leading-tight font-bold tabular-nums text-emerald-600 dark:text-emerald-400">
          +{value.toFixed(2)}
        </span>
        <span className="text-[10px] font-semibold uppercase tracking-[0.07em] text-muted-foreground">
          {isTrade ? 'Won by' : 'Net pts'}
        </span>
      </div>

      <div className="flex items-center gap-2 min-w-0">
        <TeamAvatar
          teamLogo={visual?.teamLogo ?? null}
          teamName={team?.team_name ?? name}
          ownerUsername={name}
          color={avatarColor(visual?.colorIndex ?? 0)}
        />
        <span className="min-w-0 text-[13px] font-semibold text-foreground truncate">
          {name}
        </span>
      </div>

      <div className="flex flex-col gap-0.5 pt-2 border-t border-border/50 text-[11.5px]">
        {added.length > 0 && (
          <p className="flex items-center gap-1 min-w-0 text-emerald-600 dark:text-emerald-400">
            <ArrowUp className="w-3 h-3 shrink-0" />
            <span className="sr-only">Added:</span>
            <span className="truncate">{added.join(', ')}</span>
          </p>
        )}
        {dropped.length > 0 && (
          <p className="flex items-center gap-1 min-w-0 text-red-600 dark:text-red-400">
            <ArrowDown className="w-3 h-3 shrink-0" />
            <span className="sr-only">{isTrade ? 'Gave up:' : 'Dropped:'}</span>
            <span className="truncate">{dropped.join(', ')}</span>
          </p>
        )}
        <p className="text-muted-foreground truncate mt-0.5">
          Wk {txn.week}
          {context && ` · ${context}`}
        </p>
      </div>
    </li>
  );
}

/**
 * The season's five highest-impact moves across waivers, free agents, and trades (frontend/transactions),
 * ranked by the same net-points math the transaction cards show. Renders nothing when no move
 * has a positive impact; the caller omits it entirely when box scores are unavailable.
 */
export function TopTransactions({
  transactions,
  weekly,
  visuals,
}: {
  transactions: TransactionItem[];
  weekly: WeeklyPlayerPoints;
  visuals: Visuals;
}) {
  const top = topTransactions(transactions, weekly);
  if (top.length === 0) return null;

  return (
    <section aria-labelledby="top-transactions-heading" className="mb-4">
      <h2
        id="top-transactions-heading"
        className="text-[11px] font-medium uppercase tracking-[0.08em] text-muted-foreground mb-2.5"
      >
        Top transactions
      </h2>
      <ol
        aria-labelledby="top-transactions-heading"
        className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2.5"
      >
        {top.map((impact, i) => (
          <TopTile
            key={impact.txn.transaction_id}
            impact={impact}
            rank={i + 1}
            visuals={visuals}
          />
        ))}
      </ol>
    </section>
  );
}
