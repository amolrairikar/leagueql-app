import { ArrowDown, ArrowLeftRight, ArrowUp, Trophy } from 'lucide-react';
import { type ReactNode } from 'react';

import { TeamAvatar } from '@/components/team-avatar';
import {
  type TransactionItem,
  type RosterWeeklyPoints,
  type WeeklyPlayerPoints,
  rosPointsFor,
} from '@/features/transactions/api-calls';
import { playerLabel } from '@/features/transactions/owner-summary';
import {
  type RosterExits,
  involvedRosterIds,
  netPickupValue,
  pointsInRosterLineup,
  pointsWhileRostered,
  sideTotal,
  teamLabel,
} from '@/features/transactions/transaction-impact';
import { typeMeta } from '@/features/transactions/type-meta';
import { type OwnerVisual } from '@/features/transactions/visuals';
import { avatarColor } from '@/lib/color-constants';
import { cn } from '@/lib/utils';

/**
 * A single add (green ↑) or drop (red ↓) row inside a team panel. `points`, when provided,
 * renders right-aligned in the foreground color — the player's points (a `—` placeholder for a
 * traded pick, which scores nothing).
 */
export function MoveRow({
  direction,
  points,
  children,
}: {
  direction: 'add' | 'drop';
  points?: ReactNode;
  children: ReactNode;
}) {
  const Icon = direction === 'add' ? ArrowUp : ArrowDown;
  return (
    <li
      className={cn(
        'flex items-center gap-1.5 text-[12px]',
        direction === 'add'
          ? 'text-emerald-600 dark:text-emerald-400'
          : 'text-red-600 dark:text-red-400',
      )}
    >
      <Icon className="w-3 h-3 shrink-0" />
      <span className="min-w-0 truncate">{children}</span>
      {points != null && (
        <span className="ml-auto shrink-0 text-[12px] font-medium tabular-nums text-foreground">
          {points}
        </span>
      )}
    </li>
  );
}

/**
 * One team's panel within a transaction card: its avatar, name, and the moves it received.
 *
 * For a two-team trade with matchup box scores loaded, `weekly` is non-null and each acquired
 * player shows the points they scored while on this roster; the panel gains a per-side total
 * footer, and the
 * higher-scoring side (`isWinner`) is tinted and tagged "Won".
 */
export function TeamPanel({
  txn,
  rosterId,
  isTrade,
  visual,
  weekly,
  rosterWeekly,
  exits,
  sideTotal,
  isWinner,
}: {
  txn: TransactionItem;
  rosterId: string;
  isTrade: boolean;
  visual: OwnerVisual | undefined;
  weekly: WeeklyPlayerPoints | null;
  rosterWeekly: RosterWeeklyPoints | null;
  exits: RosterExits;
  sideTotal: number | null;
  isWinner: boolean;
}) {
  const showRos = weekly != null && rosterWeekly != null;
  const tradeWeek = txn.week ?? 0;
  const adds = txn.adds.filter((a) => a.roster_id === rosterId);
  // In a trade, every drop is the other side's add, so showing both per team is
  // redundant — each team's panel shows only what it received. Waivers and free
  // agents are a single roster's own add/drop, so both are shown there.
  const drops = isTrade
    ? []
    : txn.drops.filter((d) => d.roster_id === rosterId);
  const picksIn = txn.draft_picks.filter((p) => p.to_roster_id === rosterId);
  const picksOut = isTrade
    ? []
    : txn.draft_picks.filter((p) => p.from_roster_id === rosterId);

  const team = txn.teams.find((t) => t.roster_id === rosterId);
  const teamName =
    [team?.team_name, team?.display_name].find((n) => n) ??
    `Roster ${rosterId}`;
  const ownerUsername =
    [team?.display_name, team?.team_name].find((n) => n) ??
    `Roster ${rosterId}`;
  const empty =
    adds.length === 0 &&
    drops.length === 0 &&
    picksIn.length === 0 &&
    picksOut.length === 0;

  // A traded pick scores nothing; show a muted dash so the points column still lines up.
  const pickPoints = showRos ? (
    <span className="text-muted-foreground font-normal">—</span>
  ) : undefined;

  // For a waiver / free-agent move, the net pickup value is the points the acquired player(s)
  // scored while on this roster (until a later transaction dropped or traded them away) minus the
  // ROS points the released player(s) scored — a positive net means the pickup
  // outscored what was let go. It is shown on every waiver / free-agent move for a consistent
  // footer: a pure add resolves to the added total (nothing dropped), a pure drop to the negative
  // of the dropped total (nothing added). Trades use per-side totals + a winner banner instead.
  const net =
    showRos && !isTrade && !empty
      ? netPickupValue(txn, rosterId, weekly, rosterWeekly, exits)
      : null;

  return (
    <div
      className={cn(
        'flex-1 min-w-0 rounded-lg border p-3',
        isWinner
          ? 'border-emerald-500/30 bg-emerald-500/5'
          : 'border-border/50 bg-muted/40',
      )}
    >
      <div className="flex items-center gap-2 mb-2">
        <TeamAvatar
          teamLogo={visual?.teamLogo ?? null}
          teamName={teamName}
          ownerUsername={ownerUsername}
          color={avatarColor(visual?.colorIndex ?? 0)}
        />
        <span className="min-w-0 text-[13px] font-semibold text-foreground truncate">
          {teamLabel(txn, rosterId)}
        </span>
        {isWinner && (
          <span className="ml-auto shrink-0 inline-flex items-center gap-1 text-[10px] font-semibold text-emerald-600 dark:text-emerald-400">
            <Trophy className="w-3 h-3" />
            Won
          </span>
        )}
        {/* Waivers / free agents label the right-aligned points column (adds count only while on
            this roster; drops count the rest of the season); trades convey that through their per-side total footer instead.
            Placed in the header row so it aligns vertically with the owner name/icon. */}
        {showRos && !isTrade && !empty && (
          <span className="ml-auto shrink-0 text-[10px] font-semibold uppercase tracking-[0.07em] text-muted-foreground">
            Points while rostered
          </span>
        )}
      </div>
      <ul className="flex flex-col gap-1">
        {adds.map((p) => (
          <MoveRow
            key={`add-${p.player_id}`}
            direction="add"
            points={
              showRos
                ? (isTrade
                    ? pointsWhileRostered(txn, p, weekly, exits)
                    : pointsInRosterLineup(txn, p, rosterWeekly, exits)
                  ).toFixed(2)
                : undefined
            }
          >
            {playerLabel(p)}
          </MoveRow>
        ))}
        {picksIn.map((p, i) => (
          <MoveRow key={`pickin-${i}`} direction="add" points={pickPoints}>
            {p.season} Round {p.round} pick
          </MoveRow>
        ))}
        {drops.map((p) => (
          <MoveRow
            key={`drop-${p.player_id}`}
            direction="drop"
            points={
              showRos
                ? rosPointsFor(p.player_id, tradeWeek, weekly).toFixed(2)
                : undefined
            }
          >
            {playerLabel(p)}
          </MoveRow>
        ))}
        {picksOut.map((p, i) => (
          <MoveRow key={`pickout-${i}`} direction="drop">
            {p.season} Round {p.round} pick
          </MoveRow>
        ))}
        {empty && (
          <li className="text-[12px] text-muted-foreground">No moves</li>
        )}
      </ul>
      {showRos && sideTotal != null && (
        <div className="mt-2.5 pt-2 border-t border-border/50 flex items-baseline justify-between gap-2">
          <span className="text-[10px] font-semibold uppercase tracking-[0.07em] text-muted-foreground">
            Points while rostered
          </span>
          <span
            className={cn(
              'text-[15px] font-semibold tabular-nums',
              isWinner
                ? 'text-emerald-600 dark:text-emerald-400'
                : 'text-foreground',
            )}
          >
            {sideTotal.toFixed(2)}
          </span>
        </div>
      )}
      {net != null && (
        <div className="mt-2.5 pt-2 border-t border-border/50 flex items-baseline justify-between gap-2">
          <span className="text-[10px] font-semibold uppercase tracking-[0.07em] text-muted-foreground">
            Net pickup value
          </span>
          <span
            className={cn(
              'text-[15px] font-semibold tabular-nums',
              net > 0
                ? 'text-emerald-600 dark:text-emerald-400'
                : net < 0
                  ? 'text-red-600 dark:text-red-400'
                  : 'text-foreground',
            )}
          >
            {net === 0
              ? 'Even'
              : `${net > 0 ? '+' : '-'}${Math.abs(net).toFixed(2)} pts`}
          </span>
        </div>
      )}
    </div>
  );
}

export function TransactionCard({
  txn,
  visuals,
  weekly,
  rosterWeekly,
  exits,
}: {
  txn: TransactionItem;
  visuals: Map<string, OwnerVisual>;
  weekly: WeeklyPlayerPoints | null;
  rosterWeekly: RosterWeeklyPoints | null;
  exits: RosterExits;
}) {
  const date = new Date(txn.created).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
  });

  const meta = typeMeta(txn.type);
  const isTrade = txn.type === 'trade';
  const rosterIds = involvedRosterIds(txn);

  // Two-team-trade side totals (each acquired player's points while on the receiving roster) drive
  // the per-side footers and the winner comparison, and only once the season's matchup box scores
  // have loaded.
  const showRos = isTrade && rosterIds.length === 2 && weekly != null;
  const totals = showRos
    ? rosterIds.map((rid) => sideTotal(txn, rid, weekly, exits))
    : null;
  const winnerIndex =
    totals && totals[0] !== totals[1] ? (totals[0] > totals[1] ? 0 : 1) : null;

  // Panels receive the weekly box scores for two-team trades (side totals + winner, above) and for
  // every non-trade move (waiver / free agent), where the panel shows per-player ROS points and a
  // net pickup value. Multi-team (>2 roster) trades stay unchanged (no ROS).
  const panelWeekly = weekly != null && (showRos || !isTrade) ? weekly : null;

  const panel = (rosterId: string, index: number) => (
    <TeamPanel
      key={rosterId}
      txn={txn}
      rosterId={rosterId}
      isTrade={isTrade}
      visual={visuals.get(rosterId)}
      weekly={panelWeekly}
      rosterWeekly={rosterWeekly}
      exits={exits}
      sideTotal={totals ? totals[index] : null}
      isWinner={winnerIndex === index}
    />
  );

  return (
    <div className="bg-card border border-border/50 rounded-xl p-4 shadow-sm">
      <div className="flex items-center justify-between gap-2 mb-3">
        <span
          className={cn(
            'inline-flex items-center gap-1.5 text-[11px] font-semibold px-2 py-0.5 rounded-full',
            meta.chip,
          )}
        >
          <meta.Icon className="w-3 h-3" />
          {meta.label}
        </span>
        <div className="flex items-center gap-2">
          {txn.waiver_bid != null && txn.waiver_bid > 0 && (
            <span className="inline-flex items-center text-[10.5px] font-medium px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-600 dark:text-amber-400">
              ${txn.waiver_bid} FAAB
            </span>
          )}
          <span className="text-[11px] text-muted-foreground whitespace-nowrap">
            Week {txn.week} · {date}
          </span>
        </div>
      </div>

      {isTrade && rosterIds.length === 2 ? (
        <div className="flex flex-col sm:flex-row sm:items-stretch gap-2">
          {panel(rosterIds[0], 0)}
          <div className="hidden sm:flex items-center justify-center shrink-0 px-1 text-muted-foreground">
            <ArrowLeftRight className="w-4 h-4" />
          </div>
          {panel(rosterIds[1], 1)}
        </div>
      ) : (
        <div
          className={cn(
            'grid grid-cols-1 gap-2',
            rosterIds.length > 1 && 'sm:grid-cols-2',
          )}
        >
          {rosterIds.map((rid, i) => panel(rid, i))}
        </div>
      )}

      {showRos && totals && (
        <div className="mt-3 flex flex-col items-center gap-1 text-center">
          <span className="inline-flex items-center gap-1.5 text-[12px] font-semibold tabular-nums text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 border border-emerald-500/30 rounded-full px-3 py-1">
            <Trophy className="w-3 h-3 shrink-0" />
            {winnerIndex === null
              ? 'Even — both sides scored the same'
              : `${teamLabel(txn, rosterIds[winnerIndex])} won by +${Math.abs(
                  totals[0] - totals[1],
                ).toFixed(2)} pts`}
          </span>
        </div>
      )}
    </div>
  );
}
